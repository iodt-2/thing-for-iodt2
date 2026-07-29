"""
T4 / T6 — capability discovery, the facet inventory, and search safety.
"""

import pytest

from app.services.twin_rdf_service import TwinRDFService

FIXTURE = [
    {"@id": "temp-hospital", "thing_type": "atomic",
     "properties": {"temperature": {"type": "number", "unit": "Cel"}}},
    {"@id": "temp-street", "thing_type": "atomic",
     "properties": {"temperature": {"type": "number", "unit": "Cel"},
                    "humidity": {"type": "number", "unit": "%RH"}}},
    {"@id": "weather-station", "thing_type": "composite",
     "properties": {"temperature": {"type": "number", "unit": "K"},
                    "windSpeed": {"type": "number", "unit": "m/s"}}},
    {"@id": "pm25-sensor", "thing_type": "atomic",
     "properties": {"pm25": {"type": "number", "unit": "ug/m3"}}},
    {"@id": "monitoring-system", "thing_type": "system",
     "properties": {"alarmCount": {"type": "integer"}}},
]


@pytest.fixture
def capable_things(twin_store):
    for thing in FIXTURE:
        twin_store.add_thing(dict(thing))
    return twin_store


def short_names(uris):
    return sorted(uri.split("/")[-1].replace("default-", "") for uri in uris)


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "criteria,expected",
    [
        ({"property_name": "temperature"}, ["temp-hospital", "temp-street", "weather-station"]),
        ({"property_name": "TEMP"}, ["temp-hospital", "temp-street", "weather-station"]),
        ({"property_name": "temp"}, ["temp-hospital", "temp-street", "weather-station"]),
        ({"unit": "Cel"}, ["temp-hospital", "temp-street"]),
        ({"unit": "cel"}, ["temp-hospital", "temp-street"]),
        ({"thing_type": "atomic"}, ["pm25-sensor", "temp-hospital", "temp-street"]),
        ({"thing_type": "system"}, ["monitoring-system"]),
    ],
    ids=["exact", "uppercase", "substring", "unit", "unit-case", "type-atomic", "type-system"],
)
async def test_single_criterion(capable_things, criteria, expected):
    uris = await capable_things.service.find_by_capability(
        tenant_id="default", limit=50, **criteria
    )

    assert short_names(uris) == sorted(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "criteria,expected",
    [
        ({"property_name": "temperature", "unit": "Cel"}, ["temp-hospital", "temp-street"]),
        ({"property_name": "temperature", "unit": "K"}, ["weather-station"]),
        ({"property_name": "temperature", "thing_type": "composite"}, ["weather-station"]),
        ({"property_name": "temperature", "unit": "Cel", "thing_type": "atomic"},
         ["temp-hospital", "temp-street"]),
        # Contradictory criteria must return nothing rather than falling back to OR
        ({"property_name": "temperature", "unit": "ug/m3"}, []),
    ],
)
async def test_criteria_combine_with_and(capable_things, criteria, expected):
    uris = await capable_things.service.find_by_capability(
        tenant_id="default", limit=50, **criteria
    )

    assert short_names(uris) == sorted(expected)


@pytest.mark.asyncio
async def test_other_tenants_are_invisible(twin_store):
    twin_store.add_thing({"@id": "ours", "properties": {"temperature": {"type": "number"}}})
    twin_store.add_thing(
        {"@id": "theirs", "properties": {"temperature": {"type": "number"}}}, tenant="acme"
    )

    uris = await twin_store.service.find_by_capability(
        property_name="temperature", tenant_id="default", limit=50
    )

    assert short_names(uris) == ["ours"]


# ---------------------------------------------------------------------------
# Query safety
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        'temp" } GRAPH ?g { ?x ?y ?z } #',
        "temp' . ?uri ?p ?o . FILTER(true) #",
        'x"\n}\nGROUP BY ?uri\n#',
        "temp\\",
    ],
    ids=["brace-escape", "quote-escape", "newline", "trailing-backslash"],
)
async def test_injection_attempts_neither_break_nor_widen_the_query(capable_things, payload):
    uris = await capable_things.service.find_by_capability(
        property_name=payload, tenant_id="default", limit=50
    )

    assert uris == []


@pytest.mark.asyncio
async def test_apostrophes_are_searchable(capable_things):
    """
    A single quote needs no escaping inside a double-quoted literal, and
    escaping it anyway breaks rdflib's parser — so a search for a value with
    an apostrophe must simply work.
    """
    uris = await capable_things.service.find_by_capability(
        property_name="Kadikoy'de", tenant_id="default", limit=50
    )

    assert uris == []


def test_escape_leaves_single_quotes_alone():
    escaped = TwinRDFService._escape_literal("O'Brien")

    assert escaped == "O'Brien"


@pytest.mark.parametrize(
    "raw,expected",
    [('say "hi"', 'say \\"hi\\"'), ("back\\slash", "back\\\\slash"), ("a\nb", "a\\nb")],
)
def test_escape_handles_the_characters_that_matter(raw, expected):
    assert TwinRDFService._escape_literal(raw) == expected


# ---------------------------------------------------------------------------
# Facet inventory
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inventory_reports_what_is_present(capable_things):
    inventory = await capable_things.service.list_capabilities("default")

    names = {entry["name"] for entry in inventory["properties"]}
    assert names == {"temperature", "humidity", "windSpeed", "pm25", "alarmCount"}

    temperature = next(e for e in inventory["properties"] if e["name"] == "temperature")
    assert temperature["count"] == 3
    assert sorted(temperature["units"]) == ["Cel", "K"]

    assert {entry["name"] for entry in inventory["thingTypes"]} == {"atomic", "composite", "system"}


@pytest.mark.asyncio
async def test_property_without_a_unit_gets_none(capable_things):
    inventory = await capable_things.service.list_capabilities("default")
    alarm = next(e for e in inventory["properties"] if e["name"] == "alarmCount")

    assert alarm["units"] == []


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

def test_capability_endpoint(discovery_client, capable_things):
    response = discovery_client.get(
        "/api/v2/discovery/by-capability", params={"property": "temperature", "unit": "Cel"}
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_at_least_one_criterion_is_required(discovery_client, capable_things):
    assert discovery_client.get("/api/v2/discovery/by-capability").status_code == 400


def test_capabilities_endpoint(discovery_client, capable_things):
    body = discovery_client.get("/api/v2/discovery/capabilities").json()

    assert len(body["properties"]) == 5
    assert len(body["thingTypes"]) == 3


# ---------------------------------------------------------------------------
# T6 — text index safety
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "term,must_contain",
    [
        ("temp", "name:(temp*)"),
        ("kadikoy hastane", "AND"),
        ('bozuk"girdi', "\\\""),
    ],
)
def test_lucene_query_construction(term, must_contain):
    assert must_contain in TwinRDFService._build_lucene_query(term)


def test_blank_search_builds_no_lucene_query():
    assert TwinRDFService._build_lucene_query("   ") == ""


@pytest.mark.asyncio
async def test_index_probe_rejects_a_dataset_that_matches_everything(twin_store, monkeypatch):
    """
    The reason the probe exists: on a dataset with no text index Jena does not
    raise — text:query matches every subject, so a nonsense term comes back
    with the whole store. Trusting exceptions would silently turn search into
    "return everything".
    """
    async def matches_everything(query, timeout=None):
        return {"results": {"bindings": [{"matches": {"value": "28"}}]}}

    monkeypatch.setattr(twin_store.service, "_execute_query", matches_everything)

    assert await twin_store.service._has_working_text_index() is False


@pytest.mark.asyncio
async def test_index_probe_rejects_a_dataset_that_matches_nothing(twin_store):
    """
    The other silent failure: where text:query is not implemented it quietly
    matches nothing, so search would return no results at all. rdflib behaves
    exactly that way, which makes the local store a faithful stand-in.
    """
    twin_store.add_thing({"@id": "temp-probe", "properties": {"temperature": {"type": "number"}}})

    assert await twin_store.service._has_working_text_index() is False


@pytest.mark.asyncio
async def test_index_probe_accepts_a_working_index(twin_store, monkeypatch):
    """A real index: the nonsense term finds nothing, a present token finds something."""
    async def as_if_indexed(lucene_query):
        return 0 if TwinRDFService._TEXT_PROBE_TERM in lucene_query else 3

    twin_store.add_thing({"@id": "temp-probe", "properties": {"temperature": {"type": "number"}}})
    monkeypatch.setattr(twin_store.service, "_text_query_count", as_if_indexed)

    assert await twin_store.service._has_working_text_index() is True


@pytest.mark.asyncio
async def test_probe_result_is_cached(twin_store, monkeypatch):
    calls = []

    async def counting(lucene_query):
        calls.append(lucene_query)
        return 99      # looks like "matches everything"

    monkeypatch.setattr(twin_store.service, "_text_query_count", counting)

    assert await twin_store.service._has_working_text_index() is False
    assert await twin_store.service._has_working_text_index() is False
    assert len(calls) == 1, "the probe should run once per endpoint, not per search"


@pytest.mark.asyncio
async def test_search_falls_back_when_there_is_no_index(twin_store, monkeypatch):
    """With the flag on but no usable index, search must still return matches."""
    from app.core.config import get_settings

    twin_store.add_thing({"@id": "temp-probe", "properties": {"temperature": {"type": "number"}}})

    settings = get_settings()
    monkeypatch.setattr(settings, "FUSEKI_TEXT_INDEX", True)

    results = await twin_store.service.search("temp", tenant_id="default")

    assert [item["name"] for item in results if item["type"] == "TwinInterface"] == [
        "default-temp-probe"
    ]
