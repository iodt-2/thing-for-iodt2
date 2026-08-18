"""
NETCAD adapter — earthquake digital twin and shared 3D platform services.

Base URL: https://netcad-iodt.westeurope.cloudapp.azure.com/api

Field names below were read off the live service, not off a specification;
sample responses are kept in docs/ip2/netcad-samples/ and the tests are built
on trimmed copies of them. The mapping is therefore defensive: a field that
disappears costs its attribute, never the whole import.

Three datasets produce twins. Earthquake events and simulation results do not
belong here — an event is not a thing, and Faz 2 handles them.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

from .base import (
    DatasetSpec,
    ExternalAttribute,
    ExternalLink,
    ExternalProvider,
    ExternalThing,
    as_float,
    first_value,
    slugify,
    twin_name,
)

logger = logging.getLogger(__name__)
settings = get_settings()


TOWERS_PATH = "/telecom/towers"
BUILDINGS_PATH = "/buildings/inventory"
RISK_PATH = "/risk/assessment"
HEALTH_PATH = "/system/health"


class NetcadProvider(ExternalProvider):
    """NETCAD earthquake platform."""

    key = "netcad"
    title = "NETCAD Deprem Dijital İkizi"
    default_tenant = "netcad"

    _DATASETS = {
        "towers": DatasetSpec(
            key="towers",
            title="Haberleşme kuleleri",
            path=TOWERS_PATH,
            description="Telecom towers with operator, height and district",
        ),
        "buildings": DatasetSpec(
            key="buildings",
            title="Bina envanteri",
            path=BUILDINGS_PATH,
            description="Building inventory with structural type and risk level",
        ),
        "districts": DatasetSpec(
            key="districts",
            title="İlçe sismik risk",
            path=RISK_PATH,
            description=(
                "District level seismic risk. Composite: also reads the "
                "building and tower datasets so each district contains the "
                "things already imported from them"
            ),
            thing_type="system",
            requires=("buildings", "towers"),
        ),
    }

    @property
    def base_url(self) -> str:
        return settings.NETCAD_API_URL.rstrip("/")

    @property
    def datasets(self) -> Dict[str, DatasetSpec]:
        return dict(self._DATASETS)

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    async def health(self) -> Dict[str, Any]:
        return await self.get_json(HEALTH_PATH)

    async def fetch(self, dataset: str, **params: Any) -> Any:
        if dataset == "towers":
            return await self.get_json(TOWERS_PATH)

        if dataset == "buildings":
            use_osm = params.get("use_osm", True)
            return await self.get_json(
                BUILDINGS_PATH, {"use_osm": "true" if use_osm else "false"}
            )

        if dataset == "districts":
            # A district contains its buildings and towers, so the mapping needs
            # all three payloads at once. Fetched together rather than in
            # sequence — they are independent reads.
            risk, buildings, towers = await asyncio.gather(
                self.get_json(RISK_PATH),
                self.get_json(BUILDINGS_PATH, {"use_osm": "true"}),
                self.get_json(TOWERS_PATH),
            )
            return {"risk": risk, "buildings": buildings, "towers": towers}

        raise ValueError(f"Unknown dataset for {self.key}: {dataset}")

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def map(self, dataset: str, payload: Any, tenant_id: str) -> List[ExternalThing]:
        if dataset == "towers":
            return self._map_towers(payload)
        if dataset == "buildings":
            return self._map_buildings(payload)
        if dataset == "districts":
            return self._map_districts(payload, tenant_id)
        raise ValueError(f"Unknown dataset for {self.key}: {dataset}")

    def _map_towers(self, payload: Any) -> List[ExternalThing]:
        things: List[ExternalThing] = []
        url = f"{self.base_url}{TOWERS_PATH}"

        for record in (payload or {}).get("towers", []) or []:
            external_id = first_value(record, "tower_id", "osm_id")
            if not external_id:
                logger.warning("[netcad] tower without an id — skipped")
                continue

            operator = first_value(record, "operator")
            tower_type = first_value(record, "tower_type")
            district = first_value(record, "district")

            title = " ".join(str(part) for part in (operator, tower_type) if part)
            things.append(
                ExternalThing(
                    id=f"tower-{slugify(external_id)}",
                    name=title or f"Telecom tower {external_id}",
                    description=(
                        f"{tower_type or 'Telecom tower'} operated by "
                        f"{operator or 'an unknown operator'}"
                        + (f" in {district}" if district else "")
                    ),
                    latitude=as_float(first_value(record, "latitude", "lat")),
                    longitude=as_float(first_value(record, "longitude", "lon", "lng")),
                    attributes=_attributes(
                        [
                            ("operator", operator, None),
                            ("towerType", tower_type, None),
                            ("district", district, None),
                            ("height", as_float(first_value(record, "height")), "m"),
                            ("osmId", first_value(record, "osm_id"), None),
                            ("dataSource", first_value(record, "source"), None),
                        ]
                    ),
                    external_id=str(external_id),
                    external_url=url,
                )
            )

        return things

    def _map_buildings(self, payload: Any) -> List[ExternalThing]:
        things: List[ExternalThing] = []
        url = f"{self.base_url}{BUILDINGS_PATH}"

        for record in (payload or {}).get("buildings", []) or []:
            external_id = first_value(record, "building_id", "osm_id")
            if not external_id:
                logger.warning("[netcad] building without an id — skipped")
                continue

            building_type = first_value(record, "building_type")
            district = first_value(record, "district")
            risk_level = first_value(record, "risk_level")

            things.append(
                ExternalThing(
                    id=f"building-{slugify(external_id)}",
                    name=f"{building_type or 'Building'} {external_id}",
                    description=(
                        f"{building_type or 'Building'}"
                        + (f" in {district}" if district else "")
                        + (f", risk level {risk_level}" if risk_level else "")
                    ),
                    latitude=as_float(first_value(record, "latitude", "lat")),
                    longitude=as_float(first_value(record, "longitude", "lon", "lng")),
                    attributes=_attributes(
                        [
                            ("buildingType", building_type, None),
                            ("riskLevel", risk_level, None),
                            ("district", district, None),
                            ("occupancy", first_value(record, "osm_type"), None),
                            ("dataQuality", first_value(record, "data_quality"), None),
                            ("osmId", first_value(record, "osm_id"), None),
                            ("dataSource", first_value(record, "source"), None),
                        ]
                    ),
                    external_id=str(external_id),
                    external_url=url,
                )
            )

        return things

    def _map_districts(self, payload: Any, tenant_id: str) -> List[ExternalThing]:
        """
        District twins, each containing the buildings and towers inside it.

        The service reports no coordinates for a district, so these twins have
        no geo triples and will not appear in proximity discovery. Their value
        is the relationship layer above the individual things.
        """
        payload = payload or {}
        risk = payload.get("risk") or {}
        children = _children_by_district(
            payload.get("buildings") or {}, payload.get("towers") or {}, tenant_id
        )
        url = f"{self.base_url}{RISK_PATH}"

        things: List[ExternalThing] = []
        for record in risk.get("district_risks", []) or []:
            district = first_value(record, "district")
            if not district:
                logger.warning("[netcad] district risk row without a name — skipped")
                continue

            slug = slugify(district)
            things.append(
                ExternalThing(
                    id=f"district-{slug}",
                    name=f"{district} ilçesi",
                    description=f"Seismic risk profile for {district}",
                    thing_type="system",
                    attributes=_attributes(
                        [
                            ("district", district, None),
                            ("riskScore", as_float(first_value(record, "riskScore")), None),
                            ("population", first_value(record, "population"), None),
                            ("totalBuildings", first_value(record, "totalBuildings"), None),
                            ("highRiskBuildings", first_value(record, "highRisk"), None),
                            ("mediumRiskBuildings", first_value(record, "mediumRisk"), None),
                            ("lowRiskBuildings", first_value(record, "lowRisk"), None),
                            ("expectedCasualties", first_value(record, "casualties"), None),
                            ("economicValue", first_value(record, "economicValue"), "TRY"),
                            ("expectedLoss", first_value(record, "expectedLoss"), "TRY"),
                        ]
                    ),
                    links=[
                        ExternalLink(
                            name=f"contains_{target.split('-', 1)[-1]}",
                            target=target,
                            relationship_type="contains",
                            description=f"{district} contains this thing",
                        )
                        for target in children.get(slug, [])
                    ],
                    external_id=str(district),
                    external_url=url,
                )
            )

        return things


def _children_by_district(
    buildings_payload: Dict[str, Any],
    towers_payload: Dict[str, Any],
    tenant_id: str,
) -> Dict[str, List[str]]:
    """
    District slug → names of the twins that live in it.

    Names are produced with the same rule the importer stores them under, so a
    link resolves to a real thing rather than to a plausible-looking string.
    """
    children: Dict[str, List[str]] = {}

    sources = (
        (buildings_payload.get("buildings") or [], "building", ("building_id", "osm_id")),
        (towers_payload.get("towers") or [], "tower", ("tower_id", "osm_id")),
    )

    for records, prefix, id_keys in sources:
        for record in records:
            district = first_value(record, "district")
            external_id = first_value(record, *id_keys)
            if not district or not external_id:
                continue
            thing_id = f"{prefix}-{slugify(external_id)}"
            children.setdefault(slugify(district), []).append(
                twin_name(thing_id, tenant_id)
            )

    return children


def _attributes(rows) -> List[ExternalAttribute]:
    """Build attributes, dropping the ones the source did not report."""
    return [
        ExternalAttribute(name=name, value=value, unit=unit)
        for name, value, unit in rows
        if value not in (None, "")
    ]


__all__ = ["NetcadProvider"]
