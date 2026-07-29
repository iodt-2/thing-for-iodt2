"""
T1 / T2 — Thing Description Directory behaviour.

Covers the self-description, the Thing Descriptions generated from stored
twins, and Link header paging.
"""

import json

import pytest

from app.api.v2 import discovery
from app.services.thing_description_service import to_thing_description

FIXTURE = [
    {"@id": "gateway1", "title": "Gateway", "description": "Field gateway",
     "latitude": 40.9900, "longitude": 29.0300,
     "properties": {"uptime": {"type": "integer", "unit": "s"}}},
    {"@id": "weather-station-1", "title": "Weather Station", "description": "Kadıköy station",
     "latitude": 40.9885, "longitude": 29.0270, "altitude": 32.5, "address": "Kadıköy",
     "domain_metadata": {"manufacturer": "Vaisala", "model": "WXT536", "serial_number": "SN-1"},
     "properties": {
         "temperature": {"type": "number", "unit": "Cel", "minimum": -40, "maximum": 60,
                         "description": "Air temperature", "writable": False},
         "setpoint": {"type": "number", "unit": "Cel", "writable": True},
     },
     "actions": {"calibrate": {"description": "Calibrate the sensor"}},
     "links": [{"rel": "feeds_gw", "href": "default-gateway1", "relationship_type": "feeds"}]},
    {"@id": "pm25-sensor-1", "title": "PM2.5 Sensor",
     "properties": {"pm25": {"type": "number", "unit": "ug/m3"}}},
]


@pytest.fixture
def directory(twin_store):
    # The relationship target has to exist before the thing that points at it
    for thing in FIXTURE:
        twin_store.add_thing(dict(thing))
    return twin_store


# ---------------------------------------------------------------------------
# Self-description
# ---------------------------------------------------------------------------

def test_self_description_is_a_thing_directory(discovery_client):
    response = discovery_client.get("/.well-known/wot")
    body = response.json()

    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] == "application/td+json"
    assert body["@type"] == "ThingDirectory"
    assert "https://www.w3.org/2022/wot/discovery" in body["@context"]
    assert body["security"] == "nosec_sc"


def test_self_description_points_at_the_information_model(discovery_client):
    body = discovery_client.get("/.well-known/wot").json()
    links = {link["rel"]: link for link in body.get("links", [])}

    assert links["type"]["href"].endswith("/api/v2/ontology")


@pytest.mark.parametrize("affordance", ["things", "thing", "nearby", "byCapability", "searchSPARQL"])
def test_declared_affordances(discovery_client, affordance):
    body = discovery_client.get("/.well-known/wot").json()

    assert affordance in body["properties"]


def test_extensions_are_labelled_as_such(discovery_client):
    """
    Spec-defined operations and iodt2 additions must be distinguishable, so a
    client is never misled about what is standard.
    """
    body = discovery_client.get("/.well-known/wot").json()

    assert body["properties"]["nearby"].get("ts:extension") is True
    assert "ts:extension" not in body["properties"]["things"]


def test_an_endpoint_that_does_not_exist_is_never_advertised(discovery_client):
    """
    The self-description is generated from registered routes. A declaration
    with no route behind it must be dropped rather than published.
    """
    discovery.register_affordance(
        "route_that_does_not_exist",
        kind="properties",
        name="phantom",
        href="/phantom",
        description="not served by anything",
    )
    try:
        body = discovery_client.get("/.well-known/wot").json()
        assert "phantom" not in body.get("properties", {})
    finally:
        discovery._AFFORDANCE_REGISTRY.pop("route_that_does_not_exist", None)


# ---------------------------------------------------------------------------
# Thing Description generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stored_twin_becomes_a_thing_description(directory):
    uris = await directory.service.list_interface_uris("default", limit=50)
    records = await directory.service.fetch_thing_records(uris, "default")
    record = next(r for r in records if "weather" in r["name"])

    td = to_thing_description(record, "http://testserver/api/v2")

    assert td["@type"] == ["Thing", "ts:TwinInterface"]
    assert td["title"] == "default-weather-station-1"
    assert td["properties"]["temperature"]["type"] == "number"
    assert td["properties"]["temperature"]["unit"] == "Cel"
    assert td["properties"]["temperature"]["minimum"] == -40
    assert td["properties"]["temperature"]["maximum"] == 60
    assert td["geo:lat"] == 40.9885
    assert td["ts:manufacturer"] == "Vaisala"
    assert "calibrate" in td["actions"]


@pytest.mark.asyncio
async def test_writable_maps_to_read_only_inverted(directory):
    """TD states readOnly; the twin model stores writable. They are opposites."""
    uris = await directory.service.list_interface_uris("default", limit=50)
    records = await directory.service.fetch_thing_records(uris, "default")
    record = next(r for r in records if "weather" in r["name"])

    td = to_thing_description(record, "http://testserver/api/v2")

    assert td["properties"]["temperature"]["readOnly"] is True
    assert td["properties"]["setpoint"]["readOnly"] is False


@pytest.mark.asyncio
async def test_relationships_become_links(directory):
    uris = await directory.service.list_interface_uris("default", limit=50)
    records = await directory.service.fetch_thing_records(uris, "default")
    record = next(r for r in records if "weather" in r["name"])

    td = to_thing_description(record, "http://testserver/api/v2")
    link = td["links"][0]

    assert link["rel"] == "feeds"
    assert link["href"].endswith("/things/default-gateway1")
    assert link["type"] == "application/td+json"


@pytest.mark.asyncio
async def test_missing_protocol_bindings_are_declared(directory):
    """
    The platform describes twins, it does not proxy them, so there are no
    forms. Saying so in the document beats inventing endpoints that 404.
    """
    uris = await directory.service.list_interface_uris("default", limit=50)
    records = await directory.service.fetch_thing_records(uris, "default")

    td = to_thing_description(records[0], "http://testserver/api/v2")

    assert td["ts:noProtocolBinding"] is True
    assert "forms" not in td.get("properties", {}).get("uptime", {})


# ---------------------------------------------------------------------------
# Listing and paging
# ---------------------------------------------------------------------------

def test_listing_returns_json_ld(discovery_client, directory):
    response = discovery_client.get("/api/v2/things")

    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] == "application/ld+json"
    assert response.headers["X-Total-Count"] == "3"
    assert len(response.json()) == 3


def test_following_link_headers_visits_every_thing(discovery_client, directory):
    """A client must be able to walk the directory by following rel=next."""
    seen = []
    url = "/api/v2/things?limit=2"
    hops = 0

    while url and hops < 10:
        response = discovery_client.get(url)
        seen.extend(td["title"] for td in response.json())
        link = response.headers.get("Link")
        url = link.split(">")[0][1:] if link else None
        hops += 1

    assert len(seen) == 3
    assert len(set(seen)) == 3, "a thing appeared on more than one page"


def test_last_page_has_no_next_link(discovery_client, directory):
    response = discovery_client.get("/api/v2/things?limit=2&offset=2")

    assert "Link" not in response.headers


def test_paging_does_not_split_a_thing(discovery_client, directory):
    """
    Properties and relationships multiply the rows of the detail query, so
    paging happens on interface URIs first. A page must contain whole things.
    """
    page = discovery_client.get("/api/v2/things?limit=1&offset=1").json()

    assert len(page) == 1
    assert "title" in page[0]


def test_retrieve_one_thing(discovery_client, directory):
    response = discovery_client.get("/api/v2/things/default-weather-station-1")

    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] == "application/td+json"
    assert response.json()["title"] == "default-weather-station-1"


def test_unknown_thing_is_404(discovery_client, directory):
    assert discovery_client.get("/api/v2/things/no-such-twin").status_code == 404


def test_tenants_cannot_see_each_other(discovery_client, twin_store):
    twin_store.add_thing({"@id": "ours"})
    twin_store.add_thing({"@id": "theirs"}, tenant="acme")

    default_view = discovery_client.get("/api/v2/things").json()

    assert [td["title"] for td in default_view] == ["default-ours"]


def test_listing_is_valid_json_ld(discovery_client, directory):
    for td in discovery_client.get("/api/v2/things").json():
        assert "@context" in td
        assert "@type" in td
        assert json.dumps(td)      # serialisable, no stray objects
