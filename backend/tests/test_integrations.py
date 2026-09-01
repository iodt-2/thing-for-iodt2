"""
External integration tests — mapping, provenance, idempotency, endpoints.

The payloads under tests/fixtures/netcad/ are trimmed copies of real responses
from the partner service, not invented shapes. When the partner renames a
field, these tests are what notices.

Storage is exercised against the LocalTwinStore fixture: the importer runs the
real generator and the real triple-writing code, so a provenance triple that
never reaches the graph fails the test rather than passing on a mock.
"""

import json
from pathlib import Path

import pytest
import yaml
from rdflib import URIRef

from app.core.twin_ontology import TWIN, create_interface_uri
from app.services.integrations import get_provider, list_providers
from app.services.integrations.base import slugify, twin_name
from app.services.integrations.importer import import_dataset
from app.services.integrations.netcad import NetcadProvider

FIXTURES = Path(__file__).parent / "fixtures" / "netcad"


def _payload(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class StubNetcad(NetcadProvider):
    """NETCAD adapter with its I/O replaced — mapping stays the real thing."""

    def __init__(self, overrides=None):
        self.overrides = overrides or {}
        self.calls = []

    async def health(self):
        return {"status": "active"}

    async def fetch(self, dataset, **params):
        self.calls.append((dataset, params))
        if dataset in self.overrides:
            return self.overrides[dataset]
        if dataset == "towers":
            return _payload("towers")
        if dataset == "buildings":
            return _payload("buildings")
        if dataset == "districts":
            return {
                "risk": _payload("risk"),
                "buildings": _payload("buildings"),
                "towers": _payload("towers"),
            }
        raise ValueError(dataset)


@pytest.fixture
def provider():
    return StubNetcad()


@pytest.fixture
def import_store(twin_store, monkeypatch):
    """
    Local store that also accepts writes.

    twin_store only answers queries; store_twin_yaml would talk to Fuseki. This
    routes it into the same in-memory dataset, through the real triple builders,
    so what an import wrote can be queried back.
    """
    from app.services.twin_rdf_service import TwinRDFService

    async def fake_store(self, interface_yaml, instance_yaml, thing_id, metadata=None):
        tenant = (metadata or {}).get("tenant_id", "default")
        named = twin_store.dataset.graph(
            URIRef(twin_store.graph_uri(tenant, thing_id))
        )
        twin_store.service._add_interface_to_graph(
            named, yaml.safe_load(interface_yaml), metadata
        )
        twin_store.service._add_instance_to_graph(
            named, yaml.safe_load(instance_yaml), metadata
        )
        return True

    monkeypatch.setattr(TwinRDFService, "store_twin_yaml", fake_store)
    return twin_store


def _objects(dataset, subject, predicate):
    """Objects for subject/predicate across every named graph in the dataset."""
    return [value for _, _, value, _ in dataset.quads((subject, predicate, None, None))]


def _attributes_of(store, interface_name):
    """name → value for the attribute nodes hanging off an interface."""
    interface_uri = create_interface_uri(interface_name)
    found = {}
    for attribute in _objects(store.dataset, interface_uri, TWIN.hasAttribute):
        names = _objects(store.dataset, attribute, TWIN.attributeName)
        values = _objects(store.dataset, attribute, TWIN.attributeValue)
        if names:
            found[str(names[0])] = str(values[0]) if values else ""
    return found


# ============================================================================
# Registry
# ============================================================================


def test_netcad_is_registered():
    provider = get_provider("netcad")
    assert provider.key == "netcad"
    # Imported data must not land in the default tenant
    assert provider.default_tenant == "netcad"
    assert {"towers", "buildings", "districts"} <= set(provider.datasets)


def test_unknown_provider_raises():
    with pytest.raises(KeyError):
        get_provider("no-such-partner")


def test_describe_lists_datasets_with_urls():
    described = get_provider("netcad").describe()
    keys = {dataset["key"] for dataset in described["datasets"]}
    assert keys == {"towers", "buildings", "districts"}
    assert all(dataset["url"].startswith("http") for dataset in described["datasets"])
    assert list_providers()


# ============================================================================
# Mapping
# ============================================================================


def test_slugify_transliterates_turkish():
    # A dash-substituted "beyo-lu" would collide across districts and read badly
    assert slugify("Beyoğlu") == "beyoglu"
    assert slugify("Üsküdar") == "uskudar"
    assert slugify("Kadıköy") == "kadikoy"


def test_towers_map_to_located_things(provider):
    things = provider.map("towers", _payload("towers"), "netcad")

    assert len(things) == 3
    tower = things[0]
    assert tower.id == "tower-fallback-1"
    assert tower.latitude == pytest.approx(41.022804)
    assert tower.longitude == pytest.approx(29.047482)
    assert tower.external_id == "fallback_1"
    assert tower.external_url.endswith("/telecom/towers")

    attributes = {attr.name: attr for attr in tower.attributes}
    assert attributes["operator"].value == "Turkcell"
    assert attributes["height"].value == pytest.approx(135.0)
    assert attributes["height"].unit == "m"
    assert attributes["district"].value == "Üsküdar"


def test_buildings_map_with_risk_level(provider):
    things = provider.map("buildings", _payload("buildings"), "netcad")

    assert [thing.id for thing in things] == [
        "building-fallback-1",
        "building-fallback-2",
        "building-fallback-3",
    ]
    attributes = {attr.name: attr.value for attr in things[0].attributes}
    assert attributes["buildingType"] == "RC_Low"
    assert attributes["riskLevel"] == "medium"
    assert attributes["district"] == "Beyoğlu"


def test_districts_contain_their_children(provider):
    payload = {
        "risk": _payload("risk"),
        "buildings": _payload("buildings"),
        "towers": _payload("towers"),
    }
    things = {thing.id: thing for thing in provider.map("districts", payload, "netcad")}

    beyoglu = things["district-beyoglu"]
    assert beyoglu.thing_type == "system"
    # The service reports no coordinates for a district
    assert beyoglu.latitude is None

    targets = {link.target for link in beyoglu.links}
    assert targets == {
        twin_name("building-fallback-1", "netcad"),
        twin_name("tower-fallback-3", "netcad"),
    }
    assert all(link.relationship_type == "contains" for link in beyoglu.links)

    # Üsküdar has towers but no risk row, so it produces no district twin
    assert "district-uskudar" not in things


def test_mapping_survives_missing_fields(provider):
    payload = {
        "towers": [
            {"tower_id": "t1"},  # no coordinates, no operator
            {"latitude": 41.0, "longitude": 29.0},  # no id at all
        ]
    }
    things = provider.map("towers", payload, "netcad")

    # The record without an id is dropped; the sparse one still becomes a thing
    assert len(things) == 1
    assert things[0].id == "tower-t1"
    assert things[0].latitude is None
    assert things[0].attributes == []


def test_fingerprint_changes_with_content(provider):
    first = provider.map("towers", _payload("towers"), "netcad")[0]
    again = provider.map("towers", _payload("towers"), "netcad")[0]
    assert first.fingerprint() == again.fingerprint()

    edited = _payload("towers")
    edited["towers"][0]["height"] = 999
    changed = provider.map("towers", edited, "netcad")[0]
    assert changed.fingerprint() != first.fingerprint()


# ============================================================================
# Import
# ============================================================================


@pytest.mark.asyncio
async def test_import_stores_things_with_provenance(provider, import_store):
    report = await import_dataset(provider, "towers", rdf_service=import_store.service)

    assert report.stored == 3
    assert report.tenant_id == "netcad"

    interface_name = twin_name("tower-fallback-1", "netcad")
    interface_uri = create_interface_uri(interface_name)
    objects = {
        str(predicate): str(value)
        for _, predicate, value, _ in import_store.dataset.quads(
            (interface_uri, None, None, None)
        )
    }
    assert objects[str(TWIN.externalSource)] == "netcad"
    assert objects[str(TWIN.externalId)] == "fallback_1"
    assert objects[str(TWIN.externalUrl)].endswith("/telecom/towers")
    assert objects[str(TWIN.fetchedAt)]
    assert objects[str(TWIN.contentHash)]


@pytest.mark.asyncio
async def test_import_writes_attribute_values(provider, import_store):
    await import_dataset(provider, "towers", rdf_service=import_store.service)

    attributes = _attributes_of(import_store, twin_name("tower-fallback-1", "netcad"))
    assert attributes["operator"] == "Turkcell"
    assert attributes["towerType"] == "Mobile Base Station"
    # Numeric values are typed, so 135 comes back as a decimal literal
    assert float(attributes["height"]) == pytest.approx(135.0)


@pytest.mark.asyncio
async def test_reimport_leaves_unchanged_things_alone(provider, import_store):
    first = await import_dataset(provider, "towers", rdf_service=import_store.service)
    second = await import_dataset(provider, "towers", rdf_service=import_store.service)

    assert first.stored == 3
    assert second.stored == 0
    assert second.unchanged == 3


@pytest.mark.asyncio
async def test_force_rewrites_unchanged_things(provider, import_store):
    await import_dataset(provider, "towers", rdf_service=import_store.service)
    forced = await import_dataset(
        provider, "towers", force=True, rdf_service=import_store.service
    )

    assert forced.stored == 3
    assert forced.unchanged == 0


@pytest.mark.asyncio
async def test_changed_record_is_stored_again(provider, import_store):
    await import_dataset(provider, "towers", rdf_service=import_store.service)

    edited = _payload("towers")
    edited["towers"][0]["operator"] = "Yeni Operatör"
    changed = StubNetcad(overrides={"towers": edited})

    report = await import_dataset(changed, "towers", rdf_service=import_store.service)
    assert report.stored == 1
    assert report.unchanged == 2


@pytest.mark.asyncio
async def test_dry_run_writes_nothing(provider, import_store):
    report = await import_dataset(
        provider, "towers", dry_run=True, rdf_service=import_store.service
    )

    assert report.mapped == 3
    assert report.stored == 0
    assert len(import_store.dataset) == 0


@pytest.mark.asyncio
async def test_bbox_filters_by_location(provider, import_store):
    # A box around Üsküdar keeps its two towers and drops the Beyoğlu one
    report = await import_dataset(
        provider,
        "towers",
        bbox="41.00,29.02,41.03,29.08",
        rdf_service=import_store.service,
    )

    assert report.mapped == 2
    assert report.filtered == 1


@pytest.mark.asyncio
async def test_bbox_keeps_things_without_coordinates(provider, import_store):
    # Districts have no coordinates; a box must not silently delete that layer
    report = await import_dataset(
        provider,
        "districts",
        bbox="0,0,1,1",
        dry_run=True,
        rdf_service=import_store.service,
    )

    assert report.mapped == 3
    assert report.filtered == 0


@pytest.mark.asyncio
async def test_limit_caps_the_batch(provider, import_store):
    report = await import_dataset(
        provider, "towers", limit=1, rdf_service=import_store.service
    )

    assert report.mapped == 1
    assert report.stored == 1
    assert report.filtered == 2


@pytest.mark.asyncio
async def test_links_are_dropped_when_targets_are_missing(provider, import_store):
    # districts imported first, so no building or tower exists yet
    report = await import_dataset(provider, "districts", rdf_service=import_store.service)

    assert report.stored == 3
    assert report.dropped_links == 4  # 3 buildings + 1 tower in the risk districts

    interface_uri = create_interface_uri(twin_name("district-beyoglu", "netcad"))
    relationships = list(
        import_store.dataset.quads((interface_uri, TWIN.hasRelationship, None, None))
    )
    assert relationships == []


@pytest.mark.asyncio
async def test_links_survive_when_children_are_imported_first(provider, import_store):
    await import_dataset(provider, "buildings", rdf_service=import_store.service)
    await import_dataset(provider, "towers", rdf_service=import_store.service)
    report = await import_dataset(provider, "districts", rdf_service=import_store.service)

    assert report.dropped_links == 0

    interface_uri = create_interface_uri(twin_name("district-beyoglu", "netcad"))
    targets = {
        str(target)
        for relationship in _objects(
            import_store.dataset, interface_uri, TWIN.hasRelationship
        )
        for target in _objects(import_store.dataset, relationship, TWIN.targetInterface)
    }

    assert targets == {
        str(create_interface_uri(twin_name("building-fallback-1", "netcad"))),
        str(create_interface_uri(twin_name("tower-fallback-3", "netcad"))),
    }


@pytest.mark.asyncio
async def test_unknown_dataset_is_rejected(provider, import_store):
    with pytest.raises(ValueError):
        await import_dataset(provider, "earthquakes", rdf_service=import_store.service)


@pytest.mark.asyncio
async def test_malformed_bbox_is_rejected(provider, import_store):
    with pytest.raises(ValueError):
        await import_dataset(
            provider, "towers", bbox="41,29", rdf_service=import_store.service
        )


@pytest.mark.asyncio
async def test_tenant_can_be_overridden(provider, import_store):
    report = await import_dataset(
        provider, "towers", tenant_id="demo", rdf_service=import_store.service
    )

    assert report.tenant_id == "demo"
    assert report.items[0].interface_name.startswith("demo-")


# ============================================================================
# Endpoints
# ============================================================================


@pytest.fixture
def integration_client(import_store, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.v2 import integrations as integrations_api

    stub = StubNetcad()
    monkeypatch.setattr(
        integrations_api, "get_provider", lambda key: stub if key == "netcad" else _raise(key)
    )

    app = FastAPI()
    app.include_router(integrations_api.router, prefix="/api/v2")
    return TestClient(app)


def _raise(key):
    raise KeyError(key)


def test_providers_endpoint_lists_netcad(integration_client):
    response = integration_client.get("/api/v2/integrations/providers")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert any(provider["key"] == "netcad" for provider in body["providers"])


def test_health_endpoint_passes_upstream_through(integration_client):
    response = integration_client.get("/api/v2/integrations/netcad/health")
    assert response.status_code == 200
    assert response.json()["upstream"]["status"] == "active"


def test_unknown_provider_answers_404(integration_client):
    response = integration_client.get("/api/v2/integrations/acme/health")
    assert response.status_code == 404


def test_import_endpoint_reports_what_it_stored(integration_client):
    response = integration_client.post(
        "/api/v2/integrations/netcad/import/towers?limit=2"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "netcad"
    assert body["dataset"] == "towers"
    assert body["tenant_id"] == "netcad"
    assert body["stored"] == 2


def test_import_endpoint_rejects_unknown_dataset(integration_client):
    response = integration_client.post(
        "/api/v2/integrations/netcad/import/earthquakes"
    )
    assert response.status_code == 400
