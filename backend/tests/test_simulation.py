"""
Simulation coupling — partner hazard model in, graph consequences out.

The partner side is stubbed at the HTTP boundary, so the request body the
adapter builds and the answer it parses are both exercised. Everything below
that is the real thing: the real SPARQL, the real triple writer, the real
propagation.
"""

import pytest
from rdflib import URIRef

from app.core.twin_ontology import TWIN, create_interface_uri
from app.services.integrations.base import (
    ExternalProviderError,
    HazardScenario,
    ImpactSubject,
)
from app.services.integrations.netcad import NetcadProvider
from app.services.simulation_service import run_hazard_simulation

# Kadıköy-ish, all within a couple of km of each other
EPICENTRE = HazardScenario(latitude=40.980, longitude=29.030, magnitude=6.5, depth_km=10)

NEAR = (40.981, 29.031)
ALSO_NEAR = (40.982, 29.033)
FAR = (41.500, 30.500)


class StubNetcad(NetcadProvider):
    """NETCAD with its HTTP calls replaced; mapping and body building are real."""

    def __init__(self, damages=None, error=None, events=None):
        self.damages = damages
        self.error = error
        self.events = events
        self.last_body = None

    async def post_json(self, path, body):
        self.last_body = body
        if self.error:
            return {"error": self.error}

        damages = self.damages
        if damages is None:
            # Everything sent in comes back wrecked, which keeps the seeding
            # explicit in tests that care about propagation rather than damage
            damages = [
                {
                    "building_id": building["building_id"],
                    "damage_state": "Complete",
                    "damage_probability": 1.0,
                    "pga": 2.0,
                    "distance_km": 0.2,
                    "casualties": 3,
                    "economic_loss": 100000,
                }
                for building in body["buildings"]
            ]

        return {
            "simulation_id": "sim_test_1",
            "building_damages": damages,
            "summary": {"total_buildings": len(damages)},
        }

    async def get_json(self, path, params=None):
        return {"earthquakes": self.events or []}


@pytest.fixture
def sim_store(twin_store, monkeypatch):
    """Local store that accepts graph writes and SPARQL updates."""
    from app.services.twin_rdf_service import TwinRDFService

    async def fake_store_named_graph(self, graph, graph_uri):
        named = twin_store.dataset.graph(URIRef(graph_uri))
        for triple in graph:
            named.add(triple)
        return True

    async def fake_update(self, update):
        twin_store.dataset.update(update)

    monkeypatch.setattr(TwinRDFService, "_store_named_graph", fake_store_named_graph)
    monkeypatch.setattr(TwinRDFService, "_execute_update", fake_update)
    return twin_store


def _add(store, name, coordinates=None, links=None, tenant="netcad"):
    description = {
        "@id": name,
        "title": name,
        "properties": {},
        "actions": {},
        "links": links or [],
    }
    if coordinates:
        description["latitude"], description["longitude"] = coordinates
    return store.add_thing(description, tenant=tenant)


@pytest.fixture
def chain(sim_store):
    """
    A small dependency chain around one tower:

        tower  ──feeds──▶  gateway  ──feeds──▶  dashboard
        monitor ──monitors──▶ tower
        hospital ──dependsOn──▶ tower

    Only the tower and the hospital are near the epicentre; everything else is
    far away and can only be affected through the graph.
    """
    _add(sim_store, "dashboard", coordinates=FAR)
    _add(
        sim_store,
        "gateway",
        coordinates=FAR,
        links=[{"rel": "feeds_dashboard", "href": "netcad-dashboard",
                "relationship_type": "feeds"}],
    )
    _add(
        sim_store,
        "tower",
        coordinates=NEAR,
        links=[{"rel": "feeds_gateway", "href": "netcad-gateway",
                "relationship_type": "feeds"}],
    )
    _add(
        sim_store,
        "monitor",
        coordinates=FAR,
        links=[{"rel": "monitors_tower", "href": "netcad-tower",
                "relationship_type": "monitors"}],
    )
    _add(
        sim_store,
        "hospital",
        coordinates=ALSO_NEAR,
        links=[{"rel": "depends_tower", "href": "netcad-tower",
                "relationship_type": "dependsOn"}],
    )
    return sim_store


# ============================================================================
# Adapter
# ============================================================================


@pytest.mark.asyncio
async def test_our_twins_are_sent_as_identifiable_subjects():
    provider = StubNetcad()
    subjects = [ImpactSubject("netcad-tower", 40.98, 29.03, "RC_Mid")]

    await provider.simulate(EPICENTRE, subjects)

    body = provider.last_body
    assert body["epicenter_lat"] == 40.980
    assert body["magnitude"] == 6.5
    # The twin travels under its own name, so the answer comes back keyed to
    # the graph instead of needing a coordinate match afterwards
    assert body["buildings"][0]["building_id"] == "netcad-tower"
    assert body["buildings"][0]["building_type"] == "RC_Mid"


@pytest.mark.asyncio
async def test_damage_state_drives_severity():
    provider = StubNetcad(damages=[
        {"building_id": "a", "damage_state": "Complete"},
        {"building_id": "b", "damage_state": "Moderate"},
        {"building_id": "c", "damage_state": "None"},
    ])

    outcome = await provider.simulate(EPICENTRE, [])
    severities = {impact.name: impact.severity for impact in outcome.impacts}

    assert severities == {"a": 1.0, "b": 0.5, "c": 0.0}


@pytest.mark.asyncio
async def test_probability_only_stands_in_for_an_unknown_state():
    provider = StubNetcad(damages=[
        # A state the vocabulary does not know falls back to the probability
        {"building_id": "a", "damage_state": "Pancaked", "damage_probability": 0.8},
        {"building_id": "b", "damage_probability": 0.3},
        # A known state wins over a probability that disagrees with it
        {"building_id": "c", "damage_state": "None", "damage_probability": 0.9},
    ])

    outcome = await provider.simulate(EPICENTRE, [])
    severities = {impact.name: impact.severity for impact in outcome.impacts}

    assert severities == {"a": 0.8, "b": 0.3, "c": 0.0}


@pytest.mark.asyncio
async def test_a_refused_simulation_is_an_error_not_an_empty_result():
    provider = StubNetcad(error="Epicenter coordinates required")

    with pytest.raises(ExternalProviderError):
        await provider.simulate(EPICENTRE, [])


@pytest.mark.asyncio
async def test_events_are_read_through_without_being_stored():
    provider = StubNetcad(events=[
        {"id": "725790", "magnitude": 3.3, "depth": 7.0, "latitude": 40.07,
         "longitude": 30.47, "location": "İnhisar (Bilecik)", "time": "2026-08-17T11:23:23",
         "source": "AFAD"},
        {"magnitude": 4.0},  # no id — not usable as an event reference
    ])

    events = await provider.recent_events(days=7, min_magnitude=3)

    assert len(events) == 1
    assert events[0].place == "İnhisar (Bilecik)"
    assert events[0].magnitude == pytest.approx(3.3)


# ============================================================================
# Coupling
# ============================================================================


@pytest.mark.asyncio
async def test_only_twins_near_the_epicentre_are_offered(chain):
    provider = StubNetcad()

    report = await run_hazard_simulation(
        provider, EPICENTRE, tenant_id="netcad", radius_km=5,
        rdf_service=chain.service, persist=False,
    )

    sent = {building["building_id"] for building in provider.last_body["buildings"]}
    assert sent == {"netcad-tower", "netcad-hospital"}
    assert report["subjects"] == 2


@pytest.mark.asyncio
async def test_failure_travels_through_the_graph(chain):
    provider = StubNetcad()

    report = await run_hazard_simulation(
        provider, EPICENTRE, tenant_id="netcad", radius_km=5,
        rdf_service=chain.service, persist=False,
    )

    knocked_out = {item["thing"]: item for item in report["propagated"]}

    # Nothing else was shaken; these are consequences of the tower failing
    assert set(knocked_out) == {"netcad-gateway", "netcad-monitor", "netcad-dashboard"}
    assert knocked_out["netcad-gateway"]["depth"] == 1
    assert knocked_out["netcad-gateway"]["via_thing"] == "netcad-tower"
    assert knocked_out["netcad-dashboard"]["depth"] == 2
    # The monitor is blind because what it watched is gone
    assert knocked_out["netcad-monitor"]["via_type"] == "monitors"


@pytest.mark.asyncio
async def test_light_damage_does_not_bring_down_a_chain(chain):
    provider = StubNetcad(damages=[
        {"building_id": "netcad-tower", "damage_state": "Slight"},
        {"building_id": "netcad-hospital", "damage_state": "Slight"},
    ])

    report = await run_hazard_simulation(
        provider, EPICENTRE, tenant_id="netcad", radius_km=5,
        rdf_service=chain.service, persist=False,
    )

    assert report["direct"]
    assert report["failed"] == []
    assert report["propagated"] == []


@pytest.mark.asyncio
async def test_a_run_is_stored_in_its_own_graph(chain):
    provider = StubNetcad()

    report = await run_hazard_simulation(
        provider, EPICENTRE, tenant_id="netcad", radius_km=5,
        rdf_service=chain.service,
    )

    assert report["persisted"]
    assert report["graph"] == "http://twin.io/graphs/netcad/simulation/sim_test_1"

    run_graph = chain.dataset.graph(URIRef(report["graph"]))
    kinds = [str(kind) for _s, _p, kind in run_graph.triples((None, TWIN.impactKind, None))]
    assert str(TWIN.DirectImpact) in kinds
    assert str(TWIN.PropagatedImpact) in kinds

    subjects = {
        str(subject)
        for _s, _p, subject in run_graph.triples((None, TWIN.impactSubject, None))
    }
    assert str(create_interface_uri("netcad-tower")) in subjects


@pytest.mark.asyncio
async def test_a_run_does_not_rewrite_the_twins_it_is_about(chain):
    tower_graph = URIRef(chain.graph_uri("netcad", "tower"))
    before = len(chain.dataset.graph(tower_graph))
    provider = StubNetcad()

    await run_hazard_simulation(
        provider, EPICENTRE, tenant_id="netcad", radius_km=5,
        rdf_service=chain.service,
    )

    assert len(chain.dataset.graph(tower_graph)) == before


@pytest.mark.asyncio
async def test_a_stored_run_can_be_read_back(chain):
    provider = StubNetcad()

    report = await run_hazard_simulation(
        provider, EPICENTRE, tenant_id="netcad", radius_km=5,
        rdf_service=chain.service,
    )
    stored = await chain.service.get_simulation_run(report["run_id"], tenant_id="netcad")

    assert stored["magnitude"] == pytest.approx(6.5)
    assert {item["thing"] for item in stored["direct"]} == {
        "netcad-tower", "netcad-hospital"
    }
    assert {item["thing"] for item in stored["propagated"]} == {
        "netcad-gateway", "netcad-monitor", "netcad-dashboard"
    }

    listed = await chain.service.list_simulation_runs(tenant_id="netcad")
    assert [run["run_id"] for run in listed] == ["sim_test_1"]


@pytest.mark.asyncio
async def test_relationship_status_is_left_alone_by_default(chain):
    provider = StubNetcad()

    report = await run_hazard_simulation(
        provider, EPICENTRE, tenant_id="netcad", radius_km=5,
        rdf_service=chain.service, persist=False,
    )

    assert report["degraded_relationships"] == 0
    degraded = list(
        chain.dataset.quads((None, TWIN.relationshipStatus, TWIN.Degraded, None))
    )
    assert degraded == []


@pytest.mark.asyncio
async def test_applying_status_degrades_the_affected_relationships(chain):
    provider = StubNetcad()

    report = await run_hazard_simulation(
        provider, EPICENTRE, tenant_id="netcad", radius_km=5,
        rdf_service=chain.service, persist=False, apply_status=True,
    )

    assert report["degraded_relationships"] > 0

    degraded = {
        str(relationship)
        for relationship, _p, _status, _g in chain.dataset.quads(
            (None, TWIN.relationshipStatus, TWIN.Degraded, None)
        )
    }
    # The tower's outgoing feed and the relationships pointing at it are broken
    assert any("tower" in uri for uri in degraded)
    assert len(degraded) == report["degraded_relationships"]


@pytest.mark.asyncio
async def test_an_epicentre_with_no_twins_nearby_reports_plainly(chain):
    provider = StubNetcad()

    report = await run_hazard_simulation(
        provider,
        HazardScenario(latitude=0.0, longitude=0.0, magnitude=7.0),
        tenant_id="netcad",
        rdf_service=chain.service,
    )

    assert report["subjects"] == 0
    assert report["direct"] == []
    assert report["persisted"] is False
    assert "radius" in report["note"]


@pytest.mark.asyncio
async def test_a_provider_without_simulation_is_refused(chain):
    provider = StubNetcad()
    provider.supports_simulation = False

    with pytest.raises(ValueError):
        await run_hazard_simulation(
            provider, EPICENTRE, tenant_id="netcad", rdf_service=chain.service
        )


# ============================================================================
# Endpoints
# ============================================================================


@pytest.fixture
def simulation_client(chain, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.v2 import simulation as simulation_api

    stub = StubNetcad()
    monkeypatch.setattr(
        simulation_api,
        "get_provider",
        lambda key: stub if key == "netcad" else _raise(key),
    )

    app = FastAPI()
    app.include_router(simulation_api.router, prefix="/api/v2")
    return TestClient(app)


def _raise(key):
    raise KeyError(key)


def test_earthquake_endpoint_returns_direct_and_propagated(simulation_client):
    response = simulation_client.post(
        "/api/v2/simulation/netcad/earthquake",
        json={
            "latitude": 40.980,
            "longitude": 29.030,
            "magnitude": 6.5,
            "radius_km": 5,
            "tenant": "netcad",
            "persist": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert {item["thing"] for item in body["direct"]} == {
        "netcad-tower", "netcad-hospital"
    }
    assert {item["thing"] for item in body["propagated"]} == {
        "netcad-gateway", "netcad-monitor", "netcad-dashboard"
    }


def test_earthquake_endpoint_validates_the_epicentre(simulation_client):
    response = simulation_client.post(
        "/api/v2/simulation/netcad/earthquake",
        json={"latitude": 200, "longitude": 29.0, "magnitude": 6.5},
    )

    assert response.status_code == 422


def test_unknown_provider_answers_404(simulation_client):
    response = simulation_client.post(
        "/api/v2/simulation/acme/earthquake",
        json={"latitude": 40.98, "longitude": 29.03, "magnitude": 6.5},
    )

    assert response.status_code == 404


def test_runs_endpoint_lists_what_was_stored(simulation_client):
    simulation_client.post(
        "/api/v2/simulation/netcad/earthquake",
        json={
            "latitude": 40.980,
            "longitude": 29.030,
            "magnitude": 6.5,
            "radius_km": 5,
            "tenant": "netcad",
        },
    )

    listed = simulation_client.get("/api/v2/simulation/runs?tenant=netcad").json()
    assert listed["count"] == 1

    run_id = listed["runs"][0]["run_id"]
    detail = simulation_client.get(
        f"/api/v2/simulation/runs/{run_id}?tenant=netcad"
    ).json()
    assert detail["run_id"] == run_id
    assert detail["direct"]


def test_missing_run_answers_404(simulation_client):
    response = simulation_client.get("/api/v2/simulation/runs/nope?tenant=netcad")
    assert response.status_code == 404
