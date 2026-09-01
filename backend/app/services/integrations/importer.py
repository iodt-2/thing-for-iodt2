"""
Provider-agnostic import: partner record → TwinInterface + TwinInstance → RDF.

No new RDF writing lives here. The mapped things are handed to the same
generator and the same store_twin_yaml path the create form uses, so an
imported twin is indistinguishable in structure from a hand-made one — except
that it says where it came from.

Two things this layer is responsible for and an adapter is not:

  * **Provenance.** Every imported twin carries ts:externalSource,
    ts:externalId, ts:externalUrl and ts:fetchedAt. A federated graph that
    cannot tell mirrored data from its own has no way to refresh it safely.
  * **Idempotency.** Storing replaces a named graph wholesale, so an unchanged
    record must not be stored again. The mapped record's hash is written as
    ts:contentHash and compared on the next run.
"""

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.services.twin_generator_service import TwinGeneratorService
from app.services.twin_rdf_service import TwinRDFService

from .base import ExternalProvider, ExternalThing

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ImportItem:
    """What happened to one record."""

    thing_id: str
    interface_name: str
    action: str  # stored | unchanged | filtered | failed
    detail: Optional[str] = None


@dataclass
class ImportReport:
    provider: str
    dataset: str
    tenant_id: str
    fetched_at: str
    dry_run: bool = False
    mapped: int = 0
    stored: int = 0
    unchanged: int = 0
    filtered: int = 0
    failed: int = 0
    dropped_links: int = 0
    items: List[ImportItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [asdict(item) for item in self.items]
        return payload


def _parse_bbox(bbox: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    """`min_lat,min_lon,max_lat,max_lon` → tuple, or None when not given."""
    if not bbox:
        return None
    parts = [part.strip() for part in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be 'min_lat,min_lon,max_lat,max_lon'")
    try:
        min_lat, min_lon, max_lat, max_lon = (float(part) for part in parts)
    except ValueError:
        raise ValueError("bbox values must be numbers") from None
    if min_lat > max_lat or min_lon > max_lon:
        raise ValueError("bbox minimum must not exceed its maximum")
    return min_lat, min_lon, max_lat, max_lon


def _inside_bbox(thing: ExternalThing, bbox: Tuple[float, float, float, float]) -> bool:
    """
    Whether a thing passes the box.

    A thing with no coordinates passes: the district twins carry no location
    and dropping them here would silently remove the relationship layer that
    gives the imported points their structure.
    """
    if thing.latitude is None or thing.longitude is None:
        return True
    min_lat, min_lon, max_lat, max_lon = bbox
    return min_lat <= thing.latitude <= max_lat and min_lon <= thing.longitude <= max_lon


def build_annotations(
    thing: ExternalThing, provider_key: str, fetched_at: str
) -> Dict[str, str]:
    """
    Provenance and attribute annotations for one thing.

    The YAML annotation block is the only channel into the RDF writer, so both
    kinds of metadata travel as annotations and are turned into triples there.
    """
    annotations: Dict[str, str] = {
        "external-source": provider_key,
        "fetched-at": fetched_at,
        "content-hash": thing.fingerprint(),
    }
    if thing.external_id:
        annotations["external-id"] = str(thing.external_id)
    if thing.external_url:
        annotations["external-url"] = str(thing.external_url)

    for attribute in thing.attributes:
        annotations[f"attr-{attribute.name}"] = str(attribute.value)
        if attribute.unit:
            annotations[f"attr-{attribute.name}-unit"] = str(attribute.unit)

    return annotations


def build_thing_description(thing: ExternalThing) -> Dict[str, Any]:
    """The generator's input shape, built from a mapped record."""
    return {
        "@id": thing.id,
        "title": thing.name,
        "description": thing.description,
        "latitude": thing.latitude,
        "longitude": thing.longitude,
        "altitude": thing.altitude,
        "address": thing.address,
        "properties": dict(thing.properties),
        "actions": {},
        "links": [
            {
                "rel": link.name,
                "href": link.target,
                "title": link.description,
                "relationship_type": link.relationship_type,
            }
            for link in thing.links
        ],
    }


async def _resolve_links(
    thing: ExternalThing, tenant_id: str, rdf_service: TwinRDFService
) -> int:
    """
    Drop links whose target is not in the store yet.

    Storing a relationship to a missing interface would write an inverse triple
    into a graph that does not exist, leaving a dangling edge the graph view
    then renders as a phantom node. Datasets declare their `requires` order;
    this is what happens when that order was not followed.
    """
    if not thing.links:
        return 0

    kept = []
    dropped = 0
    for link in thing.links:
        exists = await rdf_service.interface_exists(link.target, tenant_id=tenant_id)
        if exists:
            kept.append(link)
        else:
            dropped += 1
            logger.warning(
                f"[import] {thing.id}: link target '{link.target}' not found — dropped"
            )

    thing.links = kept
    return dropped


async def import_dataset(
    provider: ExternalProvider,
    dataset: str,
    *,
    tenant_id: Optional[str] = None,
    limit: Optional[int] = None,
    bbox: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    fetch_params: Optional[Dict[str, Any]] = None,
    rdf_service: Optional[TwinRDFService] = None,
) -> ImportReport:
    """
    Fetch one dataset from a provider and store it as twins.

    Args:
        provider: registered partner adapter
        dataset: dataset key the provider offers
        tenant_id: target tenant; defaults to the provider's own tenant so
            imported data never lands in `default` by accident
        limit: keep at most this many things (after bbox filtering)
        bbox: `min_lat,min_lon,max_lat,max_lon` geographic filter
        force: store even when the content hash is unchanged
        dry_run: map and report, write nothing
        fetch_params: extra query parameters for the provider call

    Raises:
        ValueError: unknown dataset, or an unusable bbox
        ExternalProviderError: partner service unreachable
    """
    if dataset not in provider.datasets:
        raise ValueError(f"Provider '{provider.key}' has no dataset '{dataset}'")

    box = _parse_bbox(bbox)
    tenant = tenant_id or provider.default_tenant
    service = rdf_service or TwinRDFService()
    generator = TwinGeneratorService()
    fetched_at = datetime.now(timezone.utc).isoformat()

    report = ImportReport(
        provider=provider.key,
        dataset=dataset,
        tenant_id=tenant,
        fetched_at=fetched_at,
        dry_run=dry_run,
    )

    payload = await provider.fetch(dataset, **(fetch_params or {}))
    things = provider.map(dataset, payload, tenant)

    if box:
        kept = [thing for thing in things if _inside_bbox(thing, box)]
        report.filtered = len(things) - len(kept)
        things = kept

    # A partner inventory can be far larger than a demo graph should hold, and
    # every thing becomes its own named graph
    ceiling = settings.EXTERNAL_IMPORT_MAX_ITEMS
    effective_limit = min(limit, ceiling) if limit else ceiling
    if len(things) > effective_limit:
        report.filtered += len(things) - effective_limit
        things = things[:effective_limit]

    report.mapped = len(things)

    for thing in things:
        interface_name = generator._normalize_name(thing.id, tenant)
        try:
            if not force:
                stored_hash = await service.get_content_hash(thing.id, tenant_id=tenant)
                if stored_hash and stored_hash == thing.fingerprint():
                    report.unchanged += 1
                    report.items.append(
                        ImportItem(thing.id, interface_name, "unchanged")
                    )
                    continue

            report.dropped_links += await _resolve_links(thing, tenant, service)

            annotations = build_annotations(thing, provider.key, fetched_at)
            description = build_thing_description(thing)

            interface_yaml = generator.generate_twin_interface_yaml(
                description,
                thing_type=thing.thing_type,
                tenant_id=tenant,
                extra_annotations=annotations,
            )
            instance_yaml = generator.generate_twin_instance_yaml(
                description, tenant_id=tenant, extra_annotations=annotations
            )

            if dry_run:
                report.items.append(
                    ImportItem(thing.id, interface_name, "stored", "dry run")
                )
                continue

            await service.store_twin_yaml(
                interface_yaml=interface_yaml,
                instance_yaml=instance_yaml,
                thing_id=thing.id,
                metadata={
                    "tenant_id": tenant,
                    "name": thing.name,
                    "description": thing.description,
                    "thing_type": thing.thing_type,
                },
            )
            report.stored += 1
            report.items.append(ImportItem(thing.id, interface_name, "stored"))

        except Exception as exc:  # one bad record must not lose the batch
            logger.error(f"[import] {provider.key}/{dataset} {thing.id} failed: {exc}")
            report.failed += 1
            report.items.append(
                ImportItem(thing.id, interface_name, "failed", str(exc))
            )

    if dry_run:
        report.stored = 0

    logger.info(
        f"[import] {provider.key}/{dataset} → tenant={tenant} "
        f"mapped={report.mapped} stored={report.stored} "
        f"unchanged={report.unchanged} failed={report.failed}"
    )
    return report


__all__ = ["import_dataset", "ImportReport", "ImportItem", "build_annotations"]
