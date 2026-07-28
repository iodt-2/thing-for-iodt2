"""
H1 — location data must reach RDF.

Regression guard for the bug where latitude/longitude/address were written into
YAML annotations and then silently dropped on the way to the graph, which made
geographic discovery impossible.
"""

import yaml
import pytest
from rdflib import Graph

from app.core.twin_ontology import (
    GEO, TWIN, add_location_triples, create_interface_uri,
)
from app.services.twin_generator_service import TwinGeneratorService
from app.services.twin_rdf_service import TwinRDFService

# Kadıköy — matches the demo scenario
LAT, LON, ALT = 40.9885, 29.0270, 32.5
ADDRESS = "Kadıköy, İstanbul"

ACCEPTANCE_QUERY = """
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX ts: <http://twin.dtd/ontology#>
SELECT ?uri ?lat ?lon ?alt ?addr WHERE {
  ?uri geo:lat ?lat ; geo:long ?lon .
  OPTIONAL { ?uri geo:alt ?alt }
  OPTIONAL { ?uri ts:address ?addr }
} ORDER BY ?uri
"""


@pytest.fixture
def thing_description():
    return {
        "@id": "geo-test-1",
        "title": "Geo Test Sensor",
        "description": "location regression fixture",
        "latitude": LAT,
        "longitude": LON,
        "altitude": ALT,
        "address": ADDRESS,
        "properties": {"temperature": {"type": "number", "unit": "Cel"}},
        "actions": {},
        "links": [],
    }


@pytest.fixture
def twin_yaml(thing_description):
    generator = TwinGeneratorService()
    return (
        generator.generate_twin_interface_yaml(thing_description, tenant_id="default"),
        generator.generate_twin_instance_yaml(thing_description, tenant_id="default"),
    )


@pytest.fixture
def twin_graph(twin_yaml):
    interface_yaml, instance_yaml = twin_yaml
    service = TwinRDFService()
    graph = Graph()
    service._add_interface_to_graph(graph, yaml.safe_load(interface_yaml), {"tenant_id": "default"})
    service._add_instance_to_graph(graph, yaml.safe_load(instance_yaml), {"tenant_id": "default"})
    return graph


def test_instance_yaml_carries_location(twin_yaml):
    """The instance is the deployed twin, so it must carry the coordinates too."""
    _, instance_yaml = twin_yaml
    annotations = yaml.safe_load(instance_yaml)["metadata"]["annotations"]

    assert annotations["latitude"] == str(LAT)
    assert annotations["longitude"] == str(LON)
    assert annotations["address"] == ADDRESS


def test_acceptance_query_returns_interface_and_instance(twin_graph):
    """The H1 acceptance query must find both subjects."""
    rows = list(twin_graph.query(ACCEPTANCE_QUERY))

    assert len(rows) == 2
    for row in rows:
        assert float(row.lat) == pytest.approx(LAT)
        assert float(row.lon) == pytest.approx(LON)
        assert float(row.alt) == pytest.approx(ALT)
        assert str(row.addr) == ADDRESS


def test_coordinates_are_typed_decimal(twin_graph):
    """Numeric typing is what makes range filters work in SPARQL."""
    from rdflib.namespace import XSD

    for predicate in (GEO.lat, GEO.long, GEO.alt):
        values = list(twin_graph.objects(None, predicate))
        assert values, f"no values for {predicate}"
        assert all(v.datatype == XSD.decimal for v in values)


@pytest.mark.parametrize(
    "annotations,expected_triples,reason",
    [
        ({"latitude": "abc", "longitude": "29.0"}, 1, "unparsable latitude is skipped"),
        ({"latitude": "91", "longitude": "29.0"}, 1, "latitude above 90 is skipped"),
        ({"latitude": "40.9", "longitude": "181"}, 1, "longitude above 180 is skipped"),
        ({"latitude": "-90", "longitude": "-180"}, 2, "range bounds are inclusive"),
        ({"latitude": "", "longitude": ""}, 0, "blank values add nothing"),
        ({}, 0, "no annotations add nothing"),
        ({"address": ADDRESS}, 1, "address alone is still recorded"),
    ],
)
def test_bad_coordinates_are_skipped_not_fatal(annotations, expected_triples, reason):
    """One bad coordinate must not cost the user the whole thing."""
    graph = Graph()
    add_location_triples(graph, create_interface_uri("bad"), annotations)

    assert len(graph) == expected_triples, reason


def test_debug_dump_matches_what_is_stored(twin_yaml):
    """
    The debug dump reimplements triple generation and had drifted — its JSON-LD
    used a ts:latitude property that does not exist in the ontology. Location is
    now shared, so the two must agree exactly.
    """
    from app.services.debug_dump_service import _build_rdf_turtle, _build_jsonld
    import json

    interface_yaml, instance_yaml = twin_yaml

    service = TwinRDFService()
    stored = Graph()
    service._add_interface_to_graph(stored, yaml.safe_load(interface_yaml), None)
    service._add_instance_to_graph(stored, yaml.safe_load(instance_yaml), None)

    dumped = Graph()
    dumped.parse(data=_build_rdf_turtle(interface_yaml, instance_yaml, None), format="turtle")

    def geo_triples(graph):
        return {(s, p, o) for s, p, o in graph if str(p).startswith(str(GEO))}

    assert geo_triples(stored) == geo_triples(dumped)

    jsonld = json.dumps(_build_jsonld("geo-test-1", interface_yaml, instance_yaml, None))
    assert "wgs84_pos#lat" in jsonld
    assert f"{TWIN}latitude" not in jsonld, "the invented ts:latitude property is back"
