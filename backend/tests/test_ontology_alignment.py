"""
H2 / H4 — the information model is anchored to standard vocabularies, and the
relationship type vocabulary is defined in exactly one place.
"""

import re
from pathlib import Path

import pytest
from rdflib import Graph, Literal, RDF, RDFS, OWL, XSD

from app.core.twin_ontology import (
    GEO, QUDT, SCHEMA, SOSA, SSN, TWIN,
    ONTOLOGY_URI, ONTOLOGY_VERSION, RELATIONSHIP_TYPES,
    get_inverse_type_map, get_relationship_types, get_twin_ontology,
)

# Alignment claims the model makes. Asserted claims must hold under reasoning;
# see the seeAlso cases below for the ones deliberately left unasserted.
ALIGNMENTS = [
    (TWIN.TwinInterface, RDFS.subClassOf, SSN.System),
    (TWIN.TwinInstance, RDFS.subClassOf, SSN.System),
    (TWIN.TwinInterface, RDFS.subClassOf, GEO.SpatialThing),
    (TWIN.TwinInstance, RDFS.subClassOf, GEO.SpatialThing),
    (TWIN.Property, RDFS.subClassOf, SSN.Property),
    (TWIN.Command, RDFS.subClassOf, SOSA.Procedure),
    (TWIN.hasProperty, RDFS.subPropertyOf, SSN.hasProperty),
    (TWIN.hasCommand, RDFS.subPropertyOf, SSN.implements),
    (TWIN.name, RDFS.subPropertyOf, RDFS.label),
    (TWIN.description, RDFS.subPropertyOf, RDFS.comment),
    (TWIN.model, RDFS.subPropertyOf, SCHEMA.model),
    (TWIN.serialNumber, RDFS.subPropertyOf, SCHEMA.serialNumber),
    (TWIN.firmwareVersion, RDFS.subPropertyOf, SCHEMA.softwareVersion),
]


@pytest.mark.parametrize("subject,predicate,obj", ALIGNMENTS, ids=lambda v: str(v).split("/")[-1])
def test_alignment_is_present(ontology, subject, predicate, obj):
    assert (subject, predicate, obj) in ontology


@pytest.mark.parametrize(
    "subject,target,reason",
    [
        (TWIN.unit, QUDT.Unit,
         "ts:unit holds a text symbol like 'Cel', not a qudt:Unit resource"),
        (TWIN.manufacturer, SCHEMA.manufacturer,
         "schema:manufacturer expects an Organization resource, we hold a name"),
    ],
)
def test_type_incompatible_links_stay_unasserted(ontology, subject, target, reason):
    """
    Where the range does not match, the model links with rdfs:seeAlso instead of
    claiming subPropertyOf. A wrong alignment is worse than none — a reasoner
    would draw false conclusions from it.
    """
    assert (subject, RDFS.seeAlso, target) in ontology, reason
    assert (subject, RDFS.subPropertyOf, target) not in ontology, reason


@pytest.mark.parametrize(
    "cls", [TWIN.TwinInterface, TWIN.TwinInstance, TWIN.Property, TWIN.Command]
)
def test_every_top_class_reaches_outside_the_ts_namespace(ontology, cls):
    external = [
        o for o in ontology.objects(cls, RDFS.subClassOf)
        if not str(o).startswith(str(TWIN))
    ]
    assert external, f"{cls} has no external superclass — the model is isolated"


def test_ontology_header(ontology):
    assert (ONTOLOGY_URI, RDF.type, OWL.Ontology) in ontology
    assert (ONTOLOGY_URI, OWL.versionInfo, Literal(ONTOLOGY_VERSION)) in ontology


@pytest.mark.parametrize("serialisation", ["turtle", "json-ld", "xml", "nt"])
def test_ontology_round_trips(ontology, serialisation):
    """Every published serialisation must parse back to the same triple count."""
    reparsed = Graph()
    reparsed.parse(data=ontology.serialize(format=serialisation), format=serialisation)

    assert len(reparsed) == len(ontology)


# ---------------------------------------------------------------------------
# H4 — relationship vocabulary derived from the ontology
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("forward,inverse", [(f, i) for f, i, *_ in RELATIONSHIP_TYPES])
def test_inverse_pairs_are_object_properties(ontology, forward, inverse):
    """
    owl:inverseOf only means something on a property. The types are also
    ts:RelationshipType individuals — OWL 2 punning makes both readings legal.
    """
    for name in (forward, inverse):
        assert (TWIN[name], RDF.type, TWIN.RelationshipType) in ontology
        assert (TWIN[name], RDF.type, OWL.ObjectProperty) in ontology

    assert (TWIN[forward], OWL.inverseOf, TWIN[inverse]) in ontology
    assert (TWIN[inverse], OWL.inverseOf, TWIN[forward]) in ontology


def test_inverse_map_is_derived_not_written():
    from app.services.twin_rdf_service import INVERSE_TYPE_MAP

    expected = {}
    for forward, inverse, *_ in RELATIONSHIP_TYPES:
        expected[forward] = inverse
        expected[inverse] = forward

    assert INVERSE_TYPE_MAP == expected
    assert get_inverse_type_map() == expected


def test_forward_and_inverse_share_a_colour():
    """An inverse is the same relation seen from the other side."""
    by_name = {t["name"]: t for t in get_relationship_types()}

    for forward, inverse, _direction, colour, _comment in RELATIONSHIP_TYPES:
        assert by_name[forward]["ui_color"] == colour
        assert by_name[inverse]["ui_color"] == colour


def test_forward_types_are_listed_before_derived_ones():
    entries = get_relationship_types()
    derived_flags = [entry["is_derived"] for entry in entries]

    assert derived_flags == sorted(derived_flags), "UI lists depend on this order"


def test_adding_a_type_to_the_ontology_is_enough():
    """
    The whole point of H4: a new relationship type must show up everywhere
    without touching Python. Added to a throwaway graph so nothing leaks.
    """
    graph = get_twin_ontology()
    before = len(get_relationship_types(graph))

    for name, derived in (("calibrates", False), ("isCalibratedBy", True)):
        graph.add((TWIN[name], RDF.type, TWIN.RelationshipType))
        graph.add((TWIN[name], RDF.type, OWL.ObjectProperty))
        graph.add((TWIN[name], RDFS.label, Literal(name, lang="en")))
        graph.add((TWIN[name], TWIN.uiColor, Literal("#0ea5e9")))
        graph.add((TWIN[name], TWIN.isDerived, Literal(derived, datatype=XSD.boolean)))
    graph.add((TWIN.calibrates, OWL.inverseOf, TWIN.isCalibratedBy))
    graph.add((TWIN.isCalibratedBy, OWL.inverseOf, TWIN.calibrates))

    assert len(get_relationship_types(graph)) == before + 2
    assert get_inverse_type_map(graph)["calibrates"] == "isCalibratedBy"


def test_service_keeps_no_private_copy_of_the_vocabulary():
    """Guards against someone reintroducing the hand-maintained dictionary."""
    source = Path(__file__).resolve().parents[1] / "app" / "services" / "twin_rdf_service.py"
    inverse_names = "|".join(inverse for _f, inverse, *_ in RELATIONSHIP_TYPES)

    literals = re.findall(rf'["\']({inverse_names})["\']', source.read_text(encoding="utf-8"))

    assert not literals, f"relationship type names hardcoded again: {literals}"
