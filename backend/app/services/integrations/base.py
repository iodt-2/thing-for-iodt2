"""
External provider contract.

IoDT2 is multi-organisation: several partners publish their own platform APIs
and the twin store has to be able to take data from any of them. Everything
partner-specific lives in one adapter class; the importer, the RDF writing
path and the REST endpoints never learn which organisation they are serving.

Adding an organisation means adding a module here and one registry entry.
"""

import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ExternalProviderError(Exception):
    """Raised when a partner service cannot be reached or answers unusably."""


# Turkish characters would otherwise be flattened to dashes by the name
# normaliser, turning "Beyoğlu" into "beyo-lu". Transliterate first.
_TRANSLITERATE = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})


def slugify(value: Any) -> str:
    """Lowercase ASCII slug usable inside a thing id."""
    text = str(value or "").translate(_TRANSLITERATE).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def twin_name(thing_id: str, tenant_id: str) -> str:
    """
    The interface/instance name a thing id turns into once stored.

    Adapters need this to point a relationship at a thing another dataset
    imported, and the naming rule belongs to the generator — not to them.
    """
    from app.services.twin_generator_service import TwinGeneratorService

    return TwinGeneratorService()._normalize_name(thing_id, tenant_id)


# ============================================================================
# Mapped data
# ============================================================================


@dataclass(frozen=True)
class ExternalAttribute:
    """
    A static fact the source system reports: an operator name, a height.

    Deliberately not a ts:Property — a property declares the schema of a value
    a twin reports and carries no value of its own. Dropping these into
    properties would silently lose every value we imported.
    """

    name: str
    value: Any
    unit: Optional[str] = None


@dataclass(frozen=True)
class ExternalLink:
    """A relationship from this thing to another thing in our store."""

    name: str
    target: str  # already-normalised interface/instance name
    relationship_type: str = "contains"
    description: Optional[str] = None


@dataclass
class ExternalThing:
    """One mapped record, ready to become a TwinInterface + TwinInstance."""

    id: str
    name: str
    description: Optional[str] = None
    thing_type: str = "atomic"

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    address: Optional[str] = None

    attributes: List[ExternalAttribute] = field(default_factory=list)
    # WoT-shaped property declarations, for sources that describe telemetry
    properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    links: List[ExternalLink] = field(default_factory=list)

    external_id: Optional[str] = None
    external_url: Optional[str] = None

    def fingerprint(self) -> str:
        """
        Hash of everything that would reach the graph.

        Nothing time-dependent goes in, so re-importing an unchanged record
        produces the same hash and the importer can leave its named graph
        alone. Adding a volatile field here would defeat that.
        """
        payload = asdict(self)
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HazardScenario:
    """What to simulate: an epicentre and how hard it shakes."""

    latitude: float
    longitude: float
    magnitude: float
    depth_km: float = 10.0
    hazard: str = "earthquake"


@dataclass(frozen=True)
class ImpactSubject:
    """One of our twins, offered to a partner's hazard model."""

    name: str
    latitude: float
    longitude: float
    structure_type: Optional[str] = None


@dataclass(frozen=True)
class DirectImpact:
    """What the partner computed for one subject."""

    name: str
    severity: float
    damage_state: Optional[str] = None
    pga: Optional[float] = None
    distance_km: Optional[float] = None
    casualties: Optional[float] = None
    economic_loss: Optional[float] = None


@dataclass
class SimulationOutcome:
    """A partner simulation, as we understood it."""

    run_id: str
    provider: str
    scenario: HazardScenario
    impacts: List[DirectImpact] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    source_url: Optional[str] = None


@dataclass(frozen=True)
class ExternalEvent:
    """A real-world event a partner reports. Not a thing — nothing is stored."""

    id: str
    time: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    magnitude: Optional[float] = None
    depth_km: Optional[float] = None
    place: Optional[str] = None
    source: Optional[str] = None


@dataclass(frozen=True)
class DatasetSpec:
    """One importable collection offered by a provider."""

    key: str
    title: str
    path: str
    description: str
    thing_type: str = "atomic"
    # Datasets whose things must be imported first, because this one links to them
    requires: tuple = ()


# ============================================================================
# Provider contract
# ============================================================================


class ExternalProvider(ABC):
    """What every partner adapter must offer."""

    key: str = ""
    title: str = ""
    default_tenant: str = "external"

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Root of the partner API, without a trailing slash."""

    @property
    @abstractmethod
    def datasets(self) -> Dict[str, DatasetSpec]:
        """Importable datasets, keyed by dataset key."""

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Liveness of the partner service, in whatever shape it reports."""

    @abstractmethod
    async def fetch(self, dataset: str, **params: Any) -> Any:
        """Raw payload for one dataset."""

    @abstractmethod
    def map(self, dataset: str, payload: Any, tenant_id: str) -> List[ExternalThing]:
        """Turn a raw payload into things. Pure — no I/O, so it stays testable."""

    # ------------------------------------------------------------------
    # Optional capabilities
    # ------------------------------------------------------------------
    # Not every partner offers these. A provider that does sets the flag and
    # implements the method; callers check the flag rather than catching
    # NotImplementedError, so an unsupported request answers cleanly.

    supports_simulation: bool = False
    supports_events: bool = False

    async def simulate(
        self, scenario: "HazardScenario", subjects: List["ImpactSubject"]
    ) -> "SimulationOutcome":
        """Run the partner's hazard model over our twins."""
        raise NotImplementedError(f"{self.key} does not offer simulation")

    async def recent_events(
        self, days: int = 7, min_magnitude: float = 3.0
    ) -> List["ExternalEvent"]:
        """Real events the partner has seen recently."""
        raise NotImplementedError(f"{self.key} does not offer an event feed")

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def dataset_url(self, dataset: str) -> str:
        spec = self.datasets.get(dataset)
        if not spec:
            return self.base_url
        return f"{self.base_url}{spec.path}"

    async def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        GET one JSON document from the partner API.

        A partner being down is an expected condition, not a bug on our side,
        so it surfaces as ExternalProviderError with the reason kept intact.
        """
        url = f"{self.base_url}{path}"
        timeout = settings.EXTERNAL_API_TIMEOUT
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise ExternalProviderError(
                f"{self.key}: {url} answered {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"{self.key}: {url} unreachable — {exc}") from exc
        except ValueError as exc:
            raise ExternalProviderError(f"{self.key}: {url} returned invalid JSON") from exc

    async def post_json(self, path: str, body: Dict[str, Any]) -> Any:
        """POST one JSON document to the partner API and read the answer."""
        url = f"{self.base_url}{path}"
        timeout = settings.EXTERNAL_API_TIMEOUT
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=body)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise ExternalProviderError(
                f"{self.key}: {url} answered {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"{self.key}: {url} unreachable — {exc}") from exc
        except ValueError as exc:
            raise ExternalProviderError(f"{self.key}: {url} returned invalid JSON") from exc

    def describe(self) -> Dict[str, Any]:
        """Provider summary for the REST layer."""
        capabilities = ["import"]
        if self.supports_simulation:
            capabilities.append("simulation")
        if self.supports_events:
            capabilities.append("events")

        return {
            "key": self.key,
            "title": self.title,
            "base_url": self.base_url,
            "default_tenant": self.default_tenant,
            "capabilities": capabilities,
            "datasets": [
                {
                    "key": spec.key,
                    "title": spec.title,
                    "description": spec.description,
                    "url": f"{self.base_url}{spec.path}",
                    "thing_type": spec.thing_type,
                    "requires": list(spec.requires),
                }
                for spec in self.datasets.values()
            ],
        }


# ============================================================================
# Mapping helpers — partner payloads are not schema-guaranteed
# ============================================================================


def first_value(record: Dict[str, Any], *keys: str) -> Optional[Any]:
    """First key that carries a usable value; None when the record has none."""
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def as_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ExternalProvider",
    "ExternalProviderError",
    "ExternalThing",
    "ExternalAttribute",
    "ExternalLink",
    "DatasetSpec",
    "HazardScenario",
    "ImpactSubject",
    "DirectImpact",
    "SimulationOutcome",
    "ExternalEvent",
    "slugify",
    "twin_name",
    "first_value",
    "as_float",
]
