"""
Seed Service

Loads the Kadıköy demo scenario into Fuseki on startup.
Idempotent — skips things that already have a named graph.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed" / "kadikoy_demo"

# Load order matters: targets must exist before sources that reference them.
_LOAD_ORDER = [
    "sismik-sensor-z1",
    "sismik-sensor-z2",
    "moda-rezidans-a",
    "moda-caddesi",
    "kadikoy-baz",
    "kadikoy-hospital",
    "bagdat-avenue",
    "weather-station-1",
    "base-station-1",
    "seismic-sensor-1",
    "temp-sensor-hospital",
    "temp-sensor-street",
    "pm25-sensor-1",
    "kadikoy-monitoring-system",
]

TENANT_ID = "default"


def _read_pair(thing_slug: str) -> Tuple[str, str]:
    d = _SEED_DIR / thing_slug
    return (
        (d / "interface.yaml").read_text(encoding="utf-8"),
        (d / "instance.yaml").read_text(encoding="utf-8"),
    )


async def load_demo_scenario(rdf_service, force: Optional[bool] = None) -> None:
    """
    Called from lifespan after Fuseki dataset is ready.

    Skips any thing whose named graph already exists, so restarts are cheap.
    That also means edits to the seed YAML never reach an environment that was
    populated by an earlier version — set SEED_FORCE_RELOAD (or pass force) to
    re-store them. Storing replaces the named graph, so no duplicates appear.
    """
    if force is None:
        force = get_settings().SEED_FORCE_RELOAD

    loaded = 0
    skipped = 0

    if force:
        logger.info("[Seed] force reload requested — existing graphs will be replaced")

    for slug in _LOAD_ORDER:
        thing_id = f"iodt2-{slug}"
        graph_uri = f"http://twin.io/graphs/{TENANT_ID}/{thing_id}"

        try:
            exists = await _graph_exists(rdf_service, graph_uri)
            if exists and not force:
                logger.debug(f"[Seed] skip {thing_id} — graph exists")
                skipped += 1
                continue

            interface_yaml, instance_yaml = _read_pair(slug)
            await rdf_service.store_twin_yaml(
                interface_yaml,
                instance_yaml,
                thing_id,
                metadata={"tenant_id": TENANT_ID},
            )
            logger.info(f"[Seed] loaded {thing_id}")
            loaded += 1

        except FileNotFoundError:
            logger.warning(f"[Seed] seed files missing for '{slug}' — skip")
        except Exception as exc:
            logger.error(f"[Seed] failed to load '{thing_id}': {exc}")

    logger.info(f"[Seed] done — loaded={loaded}, skipped={skipped}")


async def _graph_exists(rdf_service, graph_uri: str) -> bool:
    query = f"ASK {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }}"
    try:
        result = await rdf_service._execute_query(query)
        return result.get("boolean", False)
    except Exception:
        return False
