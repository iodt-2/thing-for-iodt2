"""
Hazard simulation coupled to the twin graph.

A partner platform computes ground motion and damage for a point in space.
That answers "which buildings shake". It cannot answer "which service stops
working", because it has no model of what depends on what — that lives here,
in the relationship graph.

So the split is:

  partner   epicentre + our twin coordinates → per-twin damage
  platform  damage + relationships           → who else loses function

A run is written to its own named graph and never edits the twins it is about.
Storing into a twin's graph would replace it wholesale, and a simulation is a
belief about a hypothetical, not a correction to the inventory. Degrading
relationship status is the one exception and it is opt-in.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from app.core.geo import haversine_km
from app.core.propagation import Edge, Propagation, Seed, propagate
from app.core.twin_ontology import (
    GEO,
    TWIN,
    create_interface_uri,
    get_impact_directions,
)
from app.services.integrations.base import (
    ExternalProvider,
    ExternalProviderError,
    HazardScenario,
    ImpactSubject,
)
from app.services.twin_rdf_service import TwinRDFService

logger = logging.getLogger(__name__)

# Damage at or above this counts as a failure worth propagating. Below it the
# twin is reported as damaged but is not treated as having stopped working.
DEFAULT_FAILURE_THRESHOLD = 0.5


def _safe_run_id(value: str) -> str:
    """Run ids reach a graph URI, so keep them to characters that belong there."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value or "").strip("-")
    return cleaned or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S")


def run_graph_uri(tenant_id: str, run_id: str) -> str:
    return f"http://twin.io/graphs/{tenant_id}/simulation/{run_id}"


def _select_subjects(
    located: List[Dict[str, Any]],
    scenario: HazardScenario,
    radius_km: float,
    limit: Optional[int],
) -> List[ImpactSubject]:
    """Twins close enough to the epicentre to be worth asking about."""
    within = []
    for record in located:
        distance = haversine_km(
            scenario.latitude,
            scenario.longitude,
            record["latitude"],
            record["longitude"],
        )
        if distance <= radius_km:
            within.append((distance, record))

    within.sort(key=lambda pair: pair[0])
    if limit:
        within = within[:limit]

    return [
        ImpactSubject(
            name=record["name"],
            latitude=record["latitude"],
            longitude=record["longitude"],
            structure_type=record.get("structure_type"),
        )
        for _distance, record in within
    ]


def _relationships_touching(
    edges: List[Dict[str, Any]], affected: set
) -> List[str]:
    """
    Relationship nodes with an affected twin at either end.

    Both ends count: a relationship whose target has collapsed is as broken as
    one whose source has, and the graph should say so from either side.
    """
    touched = []
    for edge in edges:
        if edge.get("source") in affected or edge.get("target") in affected:
            uri = edge.get("uri")
            if uri:
                touched.append(uri)
    return sorted(set(touched))


def build_run_graph(
    run_id: str,
    provider_key: str,
    scenario: HazardScenario,
    direct: List[Dict[str, Any]],
    propagated: List[Propagation],
    simulated_at: str,
    source_url: Optional[str] = None,
) -> Graph:
    """The RDF a run leaves behind: the scenario and one Impact node per twin."""
    graph = Graph()
    graph.bind("ts", TWIN)
    graph.bind("geo", GEO, replace=True)

    run_uri = URIRef(f"http://iodt2.com/simulation/{run_id}")
    graph.add((run_uri, RDF.type, TWIN.SimulationRun))
    graph.add((run_uri, TWIN.runId, Literal(run_id)))
    graph.add((run_uri, TWIN.simulatedAt, Literal(simulated_at, datatype=XSD.dateTime)))
    graph.add((run_uri, TWIN.hazardType, Literal(scenario.hazard)))
    graph.add((run_uri, TWIN.magnitude, Literal(scenario.magnitude, datatype=XSD.decimal)))
    graph.add((run_uri, TWIN.depthKm, Literal(scenario.depth_km, datatype=XSD.decimal)))
    graph.add((run_uri, GEO.lat, Literal(scenario.latitude, datatype=XSD.decimal)))
    graph.add((run_uri, GEO.long, Literal(scenario.longitude, datatype=XSD.decimal)))
    graph.add((run_uri, TWIN.externalSource, Literal(provider_key)))
    if source_url:
        graph.add((run_uri, TWIN.externalUrl, Literal(source_url, datatype=XSD.anyURI)))

    for index, impact in enumerate(direct):
        impact_uri = URIRef(f"{run_uri}/impact/direct/{index}")
        graph.add((impact_uri, RDF.type, TWIN.Impact))
        graph.add((impact_uri, TWIN.impactKind, TWIN.DirectImpact))
        graph.add((impact_uri, TWIN.impactSubject, create_interface_uri(impact["thing"])))
        graph.add((impact_uri, TWIN.severity,
                   Literal(impact["severity"], datatype=XSD.decimal)))
        if impact.get("damage_state"):
            graph.add((impact_uri, TWIN.damageState, Literal(impact["damage_state"])))
        if impact.get("pga") is not None:
            graph.add((impact_uri, TWIN.peakGroundAcceleration,
                       Literal(impact["pga"], datatype=XSD.decimal)))
        if impact.get("distance_km") is not None:
            graph.add((impact_uri, TWIN.distanceKm,
                       Literal(impact["distance_km"], datatype=XSD.decimal)))
        graph.add((run_uri, TWIN.hasImpact, impact_uri))

    for index, item in enumerate(propagated):
        impact_uri = URIRef(f"{run_uri}/impact/propagated/{index}")
        graph.add((impact_uri, RDF.type, TWIN.Impact))
        graph.add((impact_uri, TWIN.impactKind, TWIN.PropagatedImpact))
        graph.add((impact_uri, TWIN.impactSubject, create_interface_uri(item.thing)))
        graph.add((impact_uri, TWIN.severity, Literal(item.severity, datatype=XSD.decimal)))
        graph.add((impact_uri, TWIN.propagationDepth,
                   Literal(item.depth, datatype=XSD.integer)))
        graph.add((impact_uri, TWIN.propagatedFrom, create_interface_uri(item.via_thing)))
        if item.via_type:
            graph.add((impact_uri, TWIN.viaRelationshipType, TWIN[item.via_type]))
        graph.add((run_uri, TWIN.hasImpact, impact_uri))

    return graph


async def run_hazard_simulation(
    provider: ExternalProvider,
    scenario: HazardScenario,
    *,
    tenant_id: str,
    radius_km: float = 50.0,
    limit: Optional[int] = None,
    max_depth: int = 3,
    decay: float = 0.6,
    min_severity: float = 0.05,
    failure_threshold: float = DEFAULT_FAILURE_THRESHOLD,
    apply_status: bool = False,
    persist: bool = True,
    rdf_service: Optional[TwinRDFService] = None,
) -> Dict[str, Any]:
    """
    Run a partner hazard model over a tenant's twins and follow the failures.

    Args:
        provider: partner adapter offering simulation
        scenario: epicentre, magnitude and depth
        tenant_id: which tenant's twins take part
        radius_km: how far from the epicentre to include twins
        limit: cap on how many twins are sent to the partner
        max_depth: hops to follow away from a failed twin
        decay: severity retained per hop
        min_severity: below this a knock-on effect is not reported
        failure_threshold: damage at or above this counts as a failure and
            propagates; below it the twin is damaged but still functioning
        apply_status: also mark affected relationships ts:Degraded in the twin
            graphs. Off by default — a hypothetical must not quietly rewrite
            the live model
        persist: write the run to its own named graph

    Returns:
        A report with the direct damage, the knock-on effects and their paths

    Raises:
        ValueError: provider offers no simulation
        ExternalProviderError: partner unreachable or refusing the request
    """
    if not provider.supports_simulation:
        raise ValueError(f"Provider '{provider.key}' does not offer simulation")

    service = rdf_service or TwinRDFService()
    simulated_at = datetime.now(timezone.utc).isoformat()

    located = await service.list_located_interfaces(tenant_id=tenant_id)
    subjects = _select_subjects(located, scenario, radius_km, limit)

    if not subjects:
        logger.info(
            f"[simulation] no located twins within {radius_km} km of "
            f"{scenario.latitude},{scenario.longitude} in tenant '{tenant_id}'"
        )
        return {
            "run_id": None,
            "provider": provider.key,
            "tenant_id": tenant_id,
            "scenario": _scenario_dict(scenario),
            "subjects": 0,
            "direct": [],
            "propagated": [],
            "degraded_relationships": 0,
            "persisted": False,
            "note": "No twin with coordinates falls inside the radius",
        }

    outcome = await provider.simulate(scenario, subjects)

    direct = [
        {
            "thing": impact.name,
            "severity": round(impact.severity, 4),
            "damage_state": impact.damage_state,
            "pga": impact.pga,
            "distance_km": impact.distance_km,
            "casualties": impact.casualties,
            "economic_loss": impact.economic_loss,
        }
        for impact in outcome.impacts
    ]
    direct.sort(key=lambda item: (-item["severity"], item["thing"]))

    seeds = [
        Seed(thing=item["thing"], severity=item["severity"])
        for item in direct
        if item["severity"] >= failure_threshold
    ]

    edge_rows = await service.list_relationship_edges(tenant_id=tenant_id)
    edges = [
        Edge(
            source=row["source"],
            target=row["target"],
            type=row.get("type") or "",
            uri=row.get("uri"),
            status=row.get("status"),
        )
        for row in edge_rows
        if row.get("source") and row.get("target")
    ]

    propagated = propagate(
        edges,
        seeds,
        get_impact_directions(),
        max_depth=max_depth,
        decay=decay,
        min_severity=min_severity,
    )

    run_id = _safe_run_id(outcome.run_id or f"{provider.key}-{simulated_at}")
    graph_uri = run_graph_uri(tenant_id, run_id)

    persisted = False
    if persist:
        graph = build_run_graph(
            run_id,
            provider.key,
            scenario,
            direct,
            propagated,
            simulated_at,
            outcome.source_url,
        )
        await service.store_graph_at(graph, graph_uri)
        persisted = True

    degraded = 0
    if apply_status:
        affected = {seed.thing for seed in seeds} | {item.thing for item in propagated}
        touched = _relationships_touching(edge_rows, affected)
        degraded = await service.set_relationship_status(
            touched, status="Degraded", tenant_id=tenant_id
        )

    logger.info(
        f"[simulation] {provider.key} run={run_id} tenant={tenant_id} "
        f"subjects={len(subjects)} failed={len(seeds)} "
        f"knock-on={len(propagated)} degraded={degraded}"
    )

    return {
        "run_id": run_id,
        "provider": provider.key,
        "tenant_id": tenant_id,
        "graph": graph_uri if persisted else None,
        "simulated_at": simulated_at,
        "scenario": _scenario_dict(scenario),
        "subjects": len(subjects),
        "failure_threshold": failure_threshold,
        "failed": [seed.thing for seed in seeds],
        "direct": direct,
        "propagated": [
            {
                "thing": item.thing,
                "severity": item.severity,
                "depth": item.depth,
                "via_thing": item.via_thing,
                "via_type": item.via_type,
            }
            for item in propagated
        ],
        "summary": outcome.summary,
        "degraded_relationships": degraded,
        "persisted": persisted,
    }


def _scenario_dict(scenario: HazardScenario) -> Dict[str, Any]:
    return {
        "hazard": scenario.hazard,
        "latitude": scenario.latitude,
        "longitude": scenario.longitude,
        "magnitude": scenario.magnitude,
        "depth_km": scenario.depth_km,
    }


__all__ = [
    "run_hazard_simulation",
    "build_run_graph",
    "run_graph_uri",
    "DEFAULT_FAILURE_THRESHOLD",
]
