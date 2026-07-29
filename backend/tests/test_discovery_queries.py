"""
T5 — the saved query catalog and the read-only SPARQL discovery endpoint.
"""

import pytest
from rdflib.plugins.sparql import prepareQuery

from app.services.query_catalog_service import (
    TENANT_PLACEHOLDER, QueryCatalogService, get_query_catalog, tenant_filter,
)


@pytest.fixture(scope="module")
def catalog():
    return get_query_catalog()


# ---------------------------------------------------------------------------
# The shipped catalog
# ---------------------------------------------------------------------------

def test_catalog_is_not_empty(catalog):
    assert len(catalog.list_queries()) > 0


def test_every_shipped_query_is_valid_sparql(catalog):
    """
    A catalog entry is a search we promise works. Both the displayed form and
    the tenant substituted form have to parse.
    """
    for entry in catalog.list_queries():
        prepareQuery(entry["query"])

        rendered = catalog.render_query(entry["id"], "default")
        prepareQuery(rendered["executable"])


def test_ids_are_unique(catalog):
    ids = [entry["id"] for entry in catalog.list_queries()]

    assert len(ids) == len(set(ids))


def test_displayed_query_carries_no_placeholder(catalog):
    """The placeholder is machinery; a user editing the query must not see it."""
    for entry in catalog.list_queries():
        assert TENANT_PLACEHOLDER not in entry["query"]


def test_category_filter(catalog):
    discovery = catalog.list_queries("discovery")

    assert discovery
    assert all(entry["category"] == "discovery" for entry in discovery)
    assert len(catalog.list_queries("all")) == len(catalog.list_queries())


def test_unknown_id_returns_none(catalog):
    assert catalog.get_query("no-such-query") is None


def test_categories_are_counted(catalog):
    counts = {entry["id"]: entry["count"] for entry in catalog.categories()}

    assert sum(counts.values()) == len(catalog.list_queries())


# ---------------------------------------------------------------------------
# Tenant scoping
# ---------------------------------------------------------------------------

def test_discovery_queries_are_tenant_scoped(catalog):
    """
    Queries authored for the discovery API restrict themselves to one tenant.
    Without this a tenant-aware endpoint would quietly return other tenants'
    twins.
    """
    for entry in catalog.list_queries("discovery"):
        assert entry["tenant_scoped"] is True, entry["id"]


def test_scoping_is_reported_not_assumed(catalog):
    """
    The searches migrated from the frontend console span every tenant, exactly
    as they did there. Their behaviour is unchanged — but it is now stated.
    """
    unscoped = [e for e in catalog.list_queries() if not e["tenant_scoped"]]

    assert unscoped, "expected the migrated console queries to be reported as unscoped"


def test_render_substitutes_the_tenant(catalog):
    entry = next(e for e in catalog.list_queries("discovery"))
    rendered = catalog.render_query(entry["id"], "acme")

    assert tenant_filter("acme") in rendered["executable"]
    assert TENANT_PLACEHOLDER not in rendered["executable"]


def test_render_leaves_unscoped_queries_alone(catalog):
    entry = next(e for e in catalog.list_queries() if not e["tenant_scoped"])
    rendered = catalog.render_query(entry["id"], "acme")

    assert rendered["executable"] == entry["query"]


# ---------------------------------------------------------------------------
# Loader robustness
# ---------------------------------------------------------------------------

def test_broken_entries_are_dropped(tmp_path):
    catalog_file = tmp_path / "queries.yaml"
    catalog_file.write_text(
        """queries:
  - id: good
    category: test
    name: Good query
    description: valid
    query: "SELECT * WHERE { ?s ?p ?o }"
  - id: broken-sparql
    category: test
    name: Broken query
    description: not valid sparql
    query: "SELECT WHERE {{{ nonsense"
  - id: missing-field
    category: test
    name: No query field
  - id: good
    category: test
    name: Duplicate id
    description: same id as the first
    query: "SELECT * WHERE { ?s ?p ?o }"
""",
        encoding="utf-8",
    )

    entries = QueryCatalogService(catalog_path=catalog_file).list_queries()

    assert [entry["id"] for entry in entries] == ["good"]


def test_missing_file_is_not_fatal(tmp_path):
    service = QueryCatalogService(catalog_path=tmp_path / "absent.yaml")

    assert service.list_queries() == []


def test_invalid_yaml_is_not_fatal(tmp_path):
    catalog_file = tmp_path / "broken.yaml"
    catalog_file.write_text("queries: [ unclosed", encoding="utf-8")

    assert QueryCatalogService(catalog_path=catalog_file).list_queries() == []


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

def test_catalog_endpoint(discovery_client):
    body = discovery_client.get("/api/v2/discovery/queries").json()

    assert body["total"] > 0
    assert {"id", "category", "name", "description", "query", "tenant_scoped"} <= set(
        body["queries"][0]
    )


def test_single_query_endpoint(discovery_client, catalog):
    query_id = catalog.list_queries()[0]["id"]

    assert discovery_client.get(f"/api/v2/discovery/queries/{query_id}").status_code == 200
    assert discovery_client.get("/api/v2/discovery/queries/nope").status_code == 404


def test_running_a_saved_query(discovery_client, twin_store):
    twin_store.add_thing({"@id": "located", "latitude": 40.9, "longitude": 29.0})
    twin_store.add_thing({"@id": "unlocated"})

    body = discovery_client.get(
        "/api/v2/discovery/sparql", params={"saved": "twins-with-location"}
    ).json()

    assert body["tenant_scoped"] is True
    assert body["tenant_id"] == "default"
    assert body["count"] == 1


def test_saved_query_respects_the_tenant(discovery_client, twin_store):
    twin_store.add_thing({"@id": "ours", "latitude": 40.9, "longitude": 29.0})
    twin_store.add_thing({"@id": "theirs", "latitude": 40.9, "longitude": 29.0}, tenant="acme")

    body = discovery_client.get(
        "/api/v2/discovery/sparql", params={"saved": "twins-with-location"}
    ).json()

    assert body["count"] == 1


def test_inline_query(discovery_client, twin_store):
    twin_store.add_thing({"@id": "thing-a"})

    body = discovery_client.get(
        "/api/v2/discovery/sparql",
        params={"q": "PREFIX ts: <http://twin.dtd/ontology#> "
                     "SELECT ?name WHERE { GRAPH ?g { ?u a ts:TwinInterface ; ts:name ?name } }"},
    ).json()

    assert body["source"] == "inline"
    assert body["tenant_scoped"] is False, "a hand written query is not rewritten"
    assert "LIMIT" in body["query"], "the guard must cap the result size"


@pytest.mark.parametrize(
    "payload",
    ["# comment\nDROP ALL", "INSERT DATA { <a:b> <a:c> <a:d> }", "DELETE WHERE { ?s ?p ?o }"],
)
def test_the_guard_applies_here_too(discovery_client, payload):
    """The discovery endpoint reuses the platform guard rather than its own."""
    assert discovery_client.get(
        "/api/v2/discovery/sparql", params={"q": payload}
    ).status_code == 400


def test_a_query_is_required(discovery_client):
    assert discovery_client.get("/api/v2/discovery/sparql").status_code == 400


def test_unknown_saved_query_is_404(discovery_client):
    assert discovery_client.get(
        "/api/v2/discovery/sparql", params={"saved": "nope"}
    ).status_code == 404
