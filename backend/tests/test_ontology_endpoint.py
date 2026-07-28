"""
H3 / H4 — the ontology is published in a form other systems can consume.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rdflib import Graph

from app.api.v2 import ontology as ontology_router
from app.core.twin_ontology import ONTOLOGY_VERSION, RELATIONSHIP_TYPES


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(ontology_router.router, prefix="/api/v2")
    return TestClient(app)


# ---------------------------------------------------------------------------
# Content negotiation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "accept,expected_type,rdflib_format",
    [
        (None, "text/turtle", "turtle"),
        ("text/turtle", "text/turtle", "turtle"),
        ("application/ld+json", "application/ld+json", "json-ld"),
        ("application/rdf+xml", "application/rdf+xml", "xml"),
        ("application/n-triples", "application/n-triples", "nt"),
        ("*/*", "text/turtle", "turtle"),
        # Highest q wins
        ("text/html;q=0.9, application/ld+json;q=1.0", "application/ld+json", "json-ld"),
        # Highest q is unsupported, so fall through to the next one
        ("text/html;q=1.0, text/turtle;q=0.5", "text/turtle", "turtle"),
    ],
)
def test_negotiated_response_parses_as_rdf(client, accept, expected_type, rdflib_format):
    headers = {"Accept": accept} if accept else {}

    response = client.get("/api/v2/ontology", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] == expected_type

    graph = Graph()
    graph.parse(data=response.text, format=rdflib_format)
    assert len(graph) > 0


def test_all_serialisations_carry_the_same_triples(client):
    counts = []
    for accept, fmt in [
        ("text/turtle", "turtle"),
        ("application/ld+json", "json-ld"),
        ("application/rdf+xml", "xml"),
        ("application/n-triples", "nt"),
    ]:
        graph = Graph()
        graph.parse(data=client.get("/api/v2/ontology", headers={"Accept": accept}).text, format=fmt)
        counts.append(len(graph))

    assert len(set(counts)) == 1, f"serialisations disagree: {counts}"


def test_unsupported_accept_is_406(client):
    assert client.get("/api/v2/ontology", headers={"Accept": "text/html"}).status_code == 406


@pytest.mark.parametrize(
    "fmt,expected_type",
    [
        ("ttl", "text/turtle"),
        ("turtle", "text/turtle"),
        ("jsonld", "application/ld+json"),
        ("xml", "application/rdf+xml"),
        ("nt", "application/n-triples"),
    ],
)
def test_format_parameter_overrides_the_header(client, fmt, expected_type):
    response = client.get(f"/api/v2/ontology?format={fmt}", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] == expected_type


def test_unknown_format_is_400(client):
    assert client.get("/api/v2/ontology?format=bogus").status_code == 400


def test_cache_headers(client):
    headers = client.get("/api/v2/ontology").headers

    assert headers["etag"] == f'"{ONTOLOGY_VERSION}"'
    assert headers["vary"] == "Accept"
    assert headers["x-ontology-version"] == ONTOLOGY_VERSION


# ---------------------------------------------------------------------------
# JSON summaries
# ---------------------------------------------------------------------------

def test_classes_expose_external_alignments(client):
    body = client.get("/api/v2/ontology/classes").json()

    assert body["total"] > 0
    aligned = [t for t in body["terms"] if t["aligned_with"]]
    assert aligned, "no class reports an external alignment"

    twin_interface = next(t for t in body["terms"] if t["name"] == "TwinInterface")
    assert twin_interface["curie"] == "ts:TwinInterface"
    assert "ssn:System" in twin_interface["aligned_with"]


def test_properties_do_not_leak_relationship_types(client):
    """
    Relationship types are typed owl:ObjectProperty for the inverse pairs, but
    they are vocabulary, not structural properties — /relationship-types owns them.
    """
    body = client.get("/api/v2/ontology/properties").json()
    names = {t["name"] for t in body["terms"]}

    for forward, inverse, *_ in RELATIONSHIP_TYPES:
        assert forward not in names
        assert inverse not in names


def test_relationship_types_endpoint(client):
    body = client.get("/api/v2/ontology/relationship-types").json()

    assert body["total"] == len(RELATIONSHIP_TYPES) * 2

    by_name = {t["name"]: t for t in body["types"]}
    for forward, inverse, direction, colour, _comment in RELATIONSHIP_TYPES:
        assert by_name[forward]["inverse"] == inverse
        assert by_name[forward]["ui_color"] == colour
        assert by_name[forward]["propagation_direction"] == direction
        assert by_name[forward]["is_derived"] is False
        assert by_name[inverse]["is_derived"] is True


def test_relationship_types_can_exclude_derived(client):
    body = client.get("/api/v2/ontology/relationship-types?include_derived=false").json()

    assert body["total"] == len(RELATIONSHIP_TYPES)
    assert all(t["is_derived"] is False for t in body["types"])
