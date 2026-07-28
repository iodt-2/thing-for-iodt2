"""
Twin Framework RDF Ontology Definition

This module defines the RDF ontology for Twin Framework.
It provides namespace definitions and helper functions for working with Twin RDF data.

Ontology URI: http://twin.dtd/ontology#
Namespace Prefix: ts

Classes:
- TwinInterface: Blueprint/template for digital twins
- TwinInstance: Concrete instance of a digital twin
- Property: Data property of an interface
- Relationship: Link between interfaces
- Command: Actionable command on an interface

Properties:
- hasProperty: Links interface to its properties
- hasRelationship: Links interface to its relationships
- hasCommand: Links interface to its commands
- instanceOf: Links instance to its interface
- hasInstanceRelationship: Links instance to another instance
"""

import logging
from decimal import Decimal, InvalidOperation

from rdflib import Namespace, Graph, RDF, RDFS, XSD, OWL, Literal, URIRef
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Namespace Definitions
# ============================================================================

# Twin Ontology
TWIN = Namespace("http://twin.dtd/ontology#")
TS = TWIN  # Alias

# Twin Data (instances)
TWIN_DATA = Namespace("http://iodt2.com/")
TSD = TWIN_DATA  # Alias

# W3C Basic Geo (WGS84 lat/long) — https://www.w3.org/2003/01/geo/
GEO = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")

# Alignment target vocabularies. The twin model is anchored to these so an
# outside system can interpret it without knowing the ts: vocabulary at all.
SOSA = Namespace("http://www.w3.org/ns/sosa/")     # W3C SSN/SOSA core
SSN = Namespace("http://www.w3.org/ns/ssn/")       # W3C SSN
QUDT = Namespace("http://qudt.org/schema/qudt/")   # Units and quantities
SCHEMA = Namespace("https://schema.org/")          # Product metadata

# The ontology resource itself (namespace URI without the trailing '#')
ONTOLOGY_URI = URIRef("http://twin.dtd/ontology")
ONTOLOGY_VERSION = "2.0.0"


# ============================================================================
# Relationship Type Vocabulary — single source of truth
# ============================================================================
# Defined once here and emitted into the ontology graph. Everything downstream
# reads it back out of the graph: the Python inverse map, the REST endpoint and
# the frontend. Adding a relationship type means editing this table only.
#
# ui_color is a deliberate UI hint carried in the model so every screen renders
# a type the same way — before this, the graph view and the detail page used
# two different and conflicting palettes.

RELATIONSHIP_TYPES = (
    # forward, inverse, propagation direction, ui colour, description
    ("feeds", "isFedBy", "source-to-target", "#f59e0b",
     "The source supplies data or material to the target"),
    ("controls", "isControlledBy", "target-to-source", "#ef4444",
     "The source commands or governs the target"),
    ("contains", "isContainedIn", "bidirectional", "#8b5cf6",
     "The source physically or logically contains the target"),
    ("monitors", "isMonitoredBy", "source-to-target", "#10b981",
     "The source observes the state of the target"),
    ("dependsOn", "isDependedOnBy", "target-to-source", "#6366f1",
     "The source requires the target in order to function"),
)

# Standard namespaces
# RDF, RDFS, XSD are imported from rdflib


# ============================================================================
# Ontology Definition
# ============================================================================

def get_twin_ontology() -> Graph:
    """
    Returns the Twin ontology as an RDF Graph.

    This ontology defines the vocabulary for describing Twin Framework
    interfaces and instances in RDF format.

    Returns:
        Graph: RDFLib graph containing the ontology
    """
    g = Graph()

    # Bind namespaces
    g.bind("ts", TWIN)
    g.bind("owl", OWL)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    # replace=True: rdflib ships "geo" pre-bound to GeoSPARQL; we mean WGS84 Basic Geo
    g.bind("geo", GEO, replace=True)
    g.bind("sosa", SOSA)
    g.bind("ssn", SSN)
    g.bind("qudt", QUDT)
    g.bind("schema", SCHEMA)

    # ========================================================================
    # Ontology header
    # ========================================================================

    g.add((ONTOLOGY_URI, RDF.type, OWL.Ontology))
    g.add((ONTOLOGY_URI, RDFS.label, Literal("iodt2 Twin Ontology", lang="en")))
    g.add((ONTOLOGY_URI, RDFS.comment, Literal(
        "Vocabulary for describing digital twin interfaces and instances. "
        "Aligned with W3C SSN/SOSA, QUDT, schema.org and W3C Basic Geo.", lang="en")))
    g.add((ONTOLOGY_URI, OWL.versionInfo, Literal(ONTOLOGY_VERSION)))
    for imported in (SOSA, SSN, GEO):
        g.add((ONTOLOGY_URI, RDFS.seeAlso, URIRef(str(imported).rstrip("#/"))))

    # ========================================================================
    # Classes
    # ========================================================================

    # TwinInterface Class
    g.add((TWIN.TwinInterface, RDF.type, RDFS.Class))
    g.add((TWIN.TwinInterface, RDFS.label, Literal("Twin Interface", lang="en")))
    g.add((TWIN.TwinInterface, RDFS.comment,
           Literal("A blueprint or template for digital twins", lang="en")))

    # TwinInstance Class
    g.add((TWIN.TwinInstance, RDF.type, RDFS.Class))
    g.add((TWIN.TwinInstance, RDFS.label, Literal("Twin Instance", lang="en")))
    g.add((TWIN.TwinInstance, RDFS.comment,
           Literal("A concrete instance of a digital twin", lang="en")))

    # Property Class
    g.add((TWIN.Property, RDF.type, RDFS.Class))
    g.add((TWIN.Property, RDFS.label, Literal("Property", lang="en")))
    g.add((TWIN.Property, RDFS.comment,
           Literal("A data property of a twin interface", lang="en")))

    # Relationship Class
    g.add((TWIN.Relationship, RDF.type, RDFS.Class))
    g.add((TWIN.Relationship, RDFS.label, Literal("Relationship", lang="en")))
    g.add((TWIN.Relationship, RDFS.comment,
           Literal("A relationship between twin interfaces", lang="en")))

    # Command Class
    g.add((TWIN.Command, RDF.type, RDFS.Class))
    g.add((TWIN.Command, RDFS.label, Literal("Command", lang="en")))
    g.add((TWIN.Command, RDFS.comment,
           Literal("An actionable command on a twin interface", lang="en")))

    # InstanceRelationship Class
    g.add((TWIN.InstanceRelationship, RDF.type, RDFS.Class))
    g.add((TWIN.InstanceRelationship, RDFS.label, Literal("Instance Relationship", lang="en")))
    g.add((TWIN.InstanceRelationship, RDFS.comment,
           Literal("A relationship between twin instances", lang="en")))

    # ========================================================================
    # Properties - Interface Structure
    # ========================================================================

    # hasProperty
    g.add((TWIN.hasProperty, RDF.type, RDF.Property))
    g.add((TWIN.hasProperty, RDFS.label, Literal("has property", lang="en")))
    g.add((TWIN.hasProperty, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.hasProperty, RDFS.range, TWIN.Property))

    # hasRelationship
    g.add((TWIN.hasRelationship, RDF.type, RDF.Property))
    g.add((TWIN.hasRelationship, RDFS.label, Literal("has relationship", lang="en")))
    g.add((TWIN.hasRelationship, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.hasRelationship, RDFS.range, TWIN.Relationship))

    # sourceInterface — Relationship node'undaki kaynak interface referansı
    g.add((TWIN.sourceInterface, RDF.type, RDF.Property))
    g.add((TWIN.sourceInterface, RDFS.label, Literal("source interface", lang="en")))
    g.add((TWIN.sourceInterface, RDFS.comment,
           Literal("The TwinInterface that defines this outgoing relationship", lang="en")))
    g.add((TWIN.sourceInterface, RDFS.domain, TWIN.Relationship))
    g.add((TWIN.sourceInterface, RDFS.range, TWIN.TwinInterface))

    # hasCommand
    g.add((TWIN.hasCommand, RDF.type, RDF.Property))
    g.add((TWIN.hasCommand, RDFS.label, Literal("has command", lang="en")))
    g.add((TWIN.hasCommand, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.hasCommand, RDFS.range, TWIN.Command))

    # ========================================================================
    # Properties - Instance Structure
    # ========================================================================

    # instanceOf
    g.add((TWIN.instanceOf, RDF.type, RDF.Property))
    g.add((TWIN.instanceOf, RDFS.label, Literal("instance of", lang="en")))
    g.add((TWIN.instanceOf, RDFS.domain, TWIN.TwinInstance))
    g.add((TWIN.instanceOf, RDFS.range, TWIN.TwinInterface))

    # hasInstanceRelationship
    g.add((TWIN.hasInstanceRelationship, RDF.type, RDF.Property))
    g.add((TWIN.hasInstanceRelationship, RDFS.label, Literal("has instance relationship", lang="en")))
    g.add((TWIN.hasInstanceRelationship, RDFS.domain, TWIN.TwinInstance))
    g.add((TWIN.hasInstanceRelationship, RDFS.range, TWIN.InstanceRelationship))

    # ========================================================================
    # Properties - Metadata
    # ========================================================================

    # name
    g.add((TWIN.name, RDF.type, RDF.Property))
    g.add((TWIN.name, RDFS.label, Literal("name", lang="en")))
    g.add((TWIN.name, RDFS.range, XSD.string))

    # description
    g.add((TWIN.description, RDF.type, RDF.Property))
    g.add((TWIN.description, RDFS.label, Literal("description", lang="en")))
    g.add((TWIN.description, RDFS.range, XSD.string))

    # ========================================================================
    # Properties - Property Attributes
    # ========================================================================

    # propertyName
    g.add((TWIN.propertyName, RDF.type, RDF.Property))
    g.add((TWIN.propertyName, RDFS.domain, TWIN.Property))
    g.add((TWIN.propertyName, RDFS.range, XSD.string))

    # propertyType
    g.add((TWIN.propertyType, RDF.type, RDF.Property))
    g.add((TWIN.propertyType, RDFS.domain, TWIN.Property))
    g.add((TWIN.propertyType, RDFS.range, XSD.string))

    # writable
    g.add((TWIN.writable, RDF.type, RDF.Property))
    g.add((TWIN.writable, RDFS.domain, TWIN.Property))
    g.add((TWIN.writable, RDFS.range, XSD.boolean))

    # minimum
    g.add((TWIN.minimum, RDF.type, RDF.Property))
    g.add((TWIN.minimum, RDFS.domain, TWIN.Property))

    # maximum
    g.add((TWIN.maximum, RDF.type, RDF.Property))
    g.add((TWIN.maximum, RDFS.domain, TWIN.Property))

    # unit
    g.add((TWIN.unit, RDF.type, RDF.Property))
    g.add((TWIN.unit, RDFS.domain, TWIN.Property))
    g.add((TWIN.unit, RDFS.range, XSD.string))

    # ========================================================================
    # Relationship Type Vocabulary (SSN/SOSA inverse pattern + DTDL name-as-type)
    # ========================================================================

    g.add((TWIN.RelationshipType, RDF.type, RDFS.Class))
    g.add((TWIN.RelationshipType, RDFS.label, Literal("Relationship Type", lang="en")))

    # Metadata properties carried by every relationship type
    g.add((TWIN.propagationDirection, RDF.type, RDF.Property))
    g.add((TWIN.propagationDirection, RDFS.domain, TWIN.RelationshipType))
    g.add((TWIN.onTargetDeleted, RDF.type, RDF.Property))
    g.add((TWIN.onTargetDeleted, RDFS.domain, TWIN.RelationshipType))
    g.add((TWIN.Deactivate, RDF.type, TWIN.DeletionPolicy))

    g.add((TWIN.uiColor, RDF.type, RDF.Property))
    g.add((TWIN.uiColor, RDFS.label, Literal("UI colour", lang="en")))
    g.add((TWIN.uiColor, RDFS.comment, Literal(
        "Hex colour a user interface should use for this term, so every screen "
        "renders it consistently.", lang="en")))
    g.add((TWIN.uiColor, RDFS.range, XSD.string))

    g.add((TWIN.isDerived, RDF.type, RDF.Property))
    g.add((TWIN.isDerived, RDFS.label, Literal("is derived", lang="en")))
    g.add((TWIN.isDerived, RDFS.comment, Literal(
        "True for inverse relationship types, which the platform generates "
        "automatically rather than the user asserting them.", lang="en")))
    g.add((TWIN.isDerived, RDFS.domain, TWIN.RelationshipType))
    g.add((TWIN.isDerived, RDFS.range, XSD.boolean))

    # Each type is used two ways at once, which OWL 2 punning permits:
    #   - as an *individual* of ts:RelationshipType — this is what
    #     ts:relationshipType points at on a reified relationship node
    #   - as an *object property* — owl:inverseOf is only meaningful on a
    #     property, so without this typing the inverse pairs below say nothing
    for fwd, inv, direction, colour, comment in RELATIONSHIP_TYPES:
        for name, derived in ((fwd, False), (inv, True)):
            term = TWIN[name]
            g.add((term, RDF.type, TWIN.RelationshipType))
            g.add((term, RDF.type, OWL.ObjectProperty))
            g.add((term, RDFS.label, Literal(name, lang="en")))
            g.add((term, TWIN.uiColor, Literal(colour)))
            g.add((term, TWIN.isDerived, Literal(derived, datatype=XSD.boolean)))
            g.add((term, TWIN.propagationDirection, Literal(direction)))
            g.add((term, TWIN.onTargetDeleted, TWIN.Deactivate))

        g.add((TWIN[fwd], RDFS.comment, Literal(comment, lang="en")))
        g.add((TWIN[inv], RDFS.comment,
               Literal(f"Inverse of {fwd}: {comment[0].lower() + comment[1:]}", lang="en")))

        g.add((TWIN[fwd], OWL.inverseOf, TWIN[inv]))
        g.add((TWIN[inv], OWL.inverseOf, TWIN[fwd]))

    # ========================================================================
    # Relationship Status (reification pattern)
    # ========================================================================

    g.add((TWIN.RelationshipStatus, RDF.type, RDFS.Class))
    g.add((TWIN.RelationshipStatus, RDFS.label, Literal("Relationship Status", lang="en")))

    g.add((TWIN.Active, RDF.type, TWIN.RelationshipStatus))
    g.add((TWIN.Inactive, RDF.type, TWIN.RelationshipStatus))
    g.add((TWIN.Degraded, RDF.type, TWIN.RelationshipStatus))

    g.add((TWIN.relationshipType, RDF.type, RDF.Property))
    g.add((TWIN.relationshipType, RDFS.domain, TWIN.Relationship))
    g.add((TWIN.relationshipType, RDFS.range, TWIN.RelationshipType))

    g.add((TWIN.relationshipStatus, RDF.type, RDF.Property))
    g.add((TWIN.relationshipStatus, RDFS.domain, TWIN.Relationship))
    g.add((TWIN.relationshipStatus, RDFS.range, TWIN.RelationshipStatus))

    # owl:inverseOf is used directly (standard OWL property, no custom definition needed)

    # ========================================================================
    # Properties - Relationship Attributes
    # ========================================================================

    # relationshipName
    g.add((TWIN.relationshipName, RDF.type, RDF.Property))
    g.add((TWIN.relationshipName, RDFS.domain, TWIN.Relationship))
    g.add((TWIN.relationshipName, RDFS.range, XSD.string))

    # targetInterface
    g.add((TWIN.targetInterface, RDF.type, RDF.Property))
    g.add((TWIN.targetInterface, RDFS.domain, TWIN.Relationship))
    g.add((TWIN.targetInterface, RDFS.range, XSD.string))

    # ========================================================================
    # Properties - Command Attributes
    # ========================================================================

    # commandName
    g.add((TWIN.commandName, RDF.type, RDF.Property))
    g.add((TWIN.commandName, RDFS.domain, TWIN.Command))
    g.add((TWIN.commandName, RDFS.range, XSD.string))

    # schema
    g.add((TWIN.schema, RDF.type, RDF.Property))
    g.add((TWIN.schema, RDFS.domain, TWIN.Command))
    g.add((TWIN.schema, RDFS.range, XSD.string))  # JSON string

    # ========================================================================
    # Properties - Instance Relationship Attributes
    # ========================================================================

    # targetInstance
    g.add((TWIN.targetInstance, RDF.type, RDF.Property))
    g.add((TWIN.targetInstance, RDFS.domain, TWIN.InstanceRelationship))
    g.add((TWIN.targetInstance, RDFS.range, TWIN.TwinInstance))

    # ========================================================================
    # Properties - Provenance
    # ========================================================================

    # generatedBy
    g.add((TWIN.generatedBy, RDF.type, RDF.Property))
    g.add((TWIN.generatedBy, RDFS.label, Literal("generated by", lang="en")))
    g.add((TWIN.generatedBy, RDFS.range, XSD.string))

    # generatedAt
    g.add((TWIN.generatedAt, RDF.type, RDF.Property))
    g.add((TWIN.generatedAt, RDFS.label, Literal("generated at", lang="en")))
    g.add((TWIN.generatedAt, RDFS.range, XSD.dateTime))

    # sourceFormat
    g.add((TWIN.sourceFormat, RDF.type, RDF.Property))
    g.add((TWIN.sourceFormat, RDFS.label, Literal("source format", lang="en")))
    g.add((TWIN.sourceFormat, RDFS.range, XSD.string))

    # originalId
    g.add((TWIN.originalId, RDF.type, RDF.Property))
    g.add((TWIN.originalId, RDFS.label, Literal("original ID", lang="en")))
    g.add((TWIN.originalId, RDFS.range, XSD.string))

    # ========================================================================
    # Properties - Thing Type & Domain Metadata (Phase 1)
    # ========================================================================

    # thingType
    g.add((TWIN.thingType, RDF.type, RDF.Property))
    g.add((TWIN.thingType, RDFS.label, Literal("thing type", lang="en")))
    g.add((TWIN.thingType, RDFS.comment,
           Literal("Modeling type of the twin: device, sensor, or component", lang="en")))
    g.add((TWIN.thingType, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.thingType, RDFS.range, XSD.string))

    # manufacturer
    g.add((TWIN.manufacturer, RDF.type, RDF.Property))
    g.add((TWIN.manufacturer, RDFS.label, Literal("manufacturer", lang="en")))
    g.add((TWIN.manufacturer, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.manufacturer, RDFS.range, XSD.string))

    # model
    g.add((TWIN.model, RDF.type, RDF.Property))
    g.add((TWIN.model, RDFS.label, Literal("model", lang="en")))
    g.add((TWIN.model, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.model, RDFS.range, XSD.string))

    # serialNumber
    g.add((TWIN.serialNumber, RDF.type, RDF.Property))
    g.add((TWIN.serialNumber, RDFS.label, Literal("serial number", lang="en")))
    g.add((TWIN.serialNumber, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.serialNumber, RDFS.range, XSD.string))

    # firmwareVersion
    g.add((TWIN.firmwareVersion, RDF.type, RDF.Property))
    g.add((TWIN.firmwareVersion, RDFS.label, Literal("firmware version", lang="en")))
    g.add((TWIN.firmwareVersion, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.firmwareVersion, RDFS.range, XSD.string))

    # ========================================================================
    # Properties - DTDL Binding (Phase 2)
    # ========================================================================

    # dtdlInterface
    g.add((TWIN.dtdlInterface, RDF.type, RDF.Property))
    g.add((TWIN.dtdlInterface, RDFS.label, Literal("DTDL interface", lang="en")))
    g.add((TWIN.dtdlInterface, RDFS.comment,
           Literal("DTMI identifier of the bound DTDL interface", lang="en")))
    g.add((TWIN.dtdlInterface, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.dtdlInterface, RDFS.range, XSD.string))

    # dtdlInterfaceName
    g.add((TWIN.dtdlInterfaceName, RDF.type, RDF.Property))
    g.add((TWIN.dtdlInterfaceName, RDFS.label, Literal("DTDL interface name", lang="en")))
    g.add((TWIN.dtdlInterfaceName, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.dtdlInterfaceName, RDFS.range, XSD.string))

    # dtdlCategory
    g.add((TWIN.dtdlCategory, RDF.type, RDF.Property))
    g.add((TWIN.dtdlCategory, RDFS.label, Literal("DTDL category", lang="en")))
    g.add((TWIN.dtdlCategory, RDFS.domain, TWIN.TwinInterface))
    g.add((TWIN.dtdlCategory, RDFS.range, XSD.string))

    # ========================================================================
    # Alignment — W3C SSN/SOSA, schema.org, QUDT
    # ========================================================================
    # A consumer that knows SSN/SOSA but not ts: must still be able to read the
    # model. Every claim below is deliberately conservative: an alignment that
    # would be wrong under reasoning is recorded as rdfs:seeAlso instead of
    # asserted as subClassOf/subPropertyOf.

    # Declare ts: classes as OWL classes too, so OWL tooling picks them up
    for cls in (TWIN.TwinInterface, TWIN.TwinInstance, TWIN.Property,
                TWIN.Relationship, TWIN.Command, TWIN.InstanceRelationship,
                TWIN.RelationshipType, TWIN.RelationshipStatus):
        g.add((cls, RDF.type, OWL.Class))

    # TwinInterface / TwinInstance -> ssn:System
    # Not sosa:Platform: a Platform is specifically a *host* for other entities,
    # whereas a twin here may be a sensor, actuator, gateway or composite.
    # ssn:System covers all of those.
    g.add((TWIN.TwinInterface, RDFS.subClassOf, SSN.System))
    g.add((TWIN.TwinInstance, RDFS.subClassOf, SSN.System))

    # ts:Property -> ssn:Property
    # Not sosa:ObservableProperty: ts:Property carries a ts:writable flag, so a
    # property may be actuatable as well as observable. ssn:Property is the
    # common superclass of sosa:ObservableProperty and sosa:ActuatableProperty.
    g.add((TWIN.Property, RDFS.subClassOf, SSN.Property))
    g.add((TWIN.hasProperty, RDFS.subPropertyOf, SSN.hasProperty))

    # ts:Command -> sosa:Procedure
    # Not sosa:Actuation: an Actuation is an event that occurred, while a
    # ts:Command is the definition of an invocable operation — a Procedure.
    g.add((TWIN.Command, RDFS.subClassOf, SOSA.Procedure))
    g.add((TWIN.hasCommand, RDFS.subPropertyOf, SSN.implements))

    # Human readable labels
    g.add((TWIN.name, RDFS.subPropertyOf, RDFS.label))
    g.add((TWIN.description, RDFS.subPropertyOf, RDFS.comment))

    # Product metadata -> schema.org, only where the range genuinely matches
    g.add((TWIN.model, RDFS.subPropertyOf, SCHEMA.model))
    g.add((TWIN.serialNumber, RDFS.subPropertyOf, SCHEMA.serialNumber))
    g.add((TWIN.firmwareVersion, RDFS.subPropertyOf, SCHEMA.softwareVersion))
    # schema:manufacturer expects an Organization resource; ts:manufacturer holds
    # the manufacturer name as text, so a subPropertyOf claim would be false.
    g.add((TWIN.manufacturer, RDFS.seeAlso, SCHEMA.manufacturer))

    # Units -> QUDT
    # qudt:unit ranges over qudt:Unit resources, while ts:unit holds a unit
    # *symbol* as text (e.g. "Cel"). Linked rather than declared a subproperty.
    g.add((TWIN.unit, RDFS.seeAlso, QUDT.Unit))
    g.add((TWIN.unit, RDFS.comment, Literal(
        "Unit symbol of the property value as text (UCUM/QUDT symbol, e.g. 'Cel'). "
        "Not a reference to a qudt:Unit resource.", lang="en")))

    # ========================================================================
    # Spatial / Location (W3C Basic Geo — WGS84)
    # ========================================================================

    # Twin'ler uzayda konumlanabilen varlıklardır. geo:lat/long/alt'ın
    # rdfs:domain'i geo:SpatialThing olduğu için bu bağ olmadan konum
    # triple'ları vokabüler açısından tutarsız kalır.
    g.add((TWIN.TwinInterface, RDFS.subClassOf, GEO.SpatialThing))
    g.add((TWIN.TwinInstance, RDFS.subClassOf, GEO.SpatialThing))

    # address — Basic Geo'da karşılığı yok, ts: altında tanımlanır
    g.add((TWIN.address, RDF.type, RDF.Property))
    g.add((TWIN.address, RDFS.label, Literal("address", lang="en")))
    g.add((TWIN.address, RDFS.comment,
           Literal("Human readable postal or administrative address of the twin", lang="en")))
    g.add((TWIN.address, RDFS.domain, GEO.SpatialThing))
    g.add((TWIN.address, RDFS.range, XSD.string))

    # ========================================================================
    # Properties - Relationship fix: targetInterface range is TwinInterface URI
    # ========================================================================

    # targetInterface range'ini string'den TwinInterface'e güncelle
    g.remove((TWIN.targetInterface, RDFS.range, None))
    g.add((TWIN.targetInterface, RDFS.range, TWIN.TwinInterface))

    return g


# ============================================================================
# Ontology Access
# ============================================================================

# The ontology is built from code and never mutated at runtime, so one shared
# instance serves every reader instead of rebuilding it per call.
_ontology_cache: Optional[Graph] = None


def get_cached_ontology() -> Graph:
    """
    Shared read-only ontology graph.

    Use this for lookups. Use get_twin_ontology() when you need a private copy
    (for example before serialising it somewhere that might modify it).
    """
    global _ontology_cache
    if _ontology_cache is None:
        _ontology_cache = get_twin_ontology()
    return _ontology_cache


def get_relationship_types(graph: Optional[Graph] = None) -> List[Dict[str, Any]]:
    """
    Read the relationship type vocabulary back out of the ontology.

    This is the only supported way to enumerate relationship types. Nothing
    downstream should keep its own list — adding a type to RELATIONSHIP_TYPES
    must be enough to make it appear everywhere.

    Returns:
        List of dicts with: name, uri, label, description, inverse,
        propagation_direction, on_target_deleted, ui_color, is_derived
    """
    g = graph if graph is not None else get_cached_ontology()

    types: List[Dict[str, Any]] = []
    for term in g.subjects(RDF.type, TWIN.RelationshipType):
        name = str(term).split("#")[-1]
        inverse = g.value(term, OWL.inverseOf)
        deletion_policy = g.value(term, TWIN.onTargetDeleted)
        is_derived = g.value(term, TWIN.isDerived)

        types.append({
            "name": name,
            "uri": str(term),
            "label": str(g.value(term, RDFS.label) or name),
            "description": str(g.value(term, RDFS.comment) or ""),
            "inverse": str(inverse).split("#")[-1] if inverse else None,
            "propagation_direction": str(g.value(term, TWIN.propagationDirection) or ""),
            "on_target_deleted": str(deletion_policy).split("#")[-1] if deletion_policy else None,
            "ui_color": str(g.value(term, TWIN.uiColor) or ""),
            "is_derived": bool(is_derived.toPython()) if is_derived is not None else False,
        })

    # Forward types first, then alphabetical — stable order for UI lists
    return sorted(types, key=lambda t: (t["is_derived"], t["name"]))


def get_inverse_type_map(graph: Optional[Graph] = None) -> Dict[str, str]:
    """
    Map every relationship type to its inverse, derived from owl:inverseOf.

    Replaces the hand-written dictionary that used to live in
    TwinRDFService and drift out of step with the ontology.
    """
    return {
        entry["name"]: entry["inverse"]
        for entry in get_relationship_types(graph)
        if entry["inverse"]
    }


# ============================================================================
# Helper Functions
# ============================================================================

def create_interface_uri(interface_name: str) -> URIRef:
    """Create URI for a TwinInterface"""
    return URIRef(f"{TWIN_DATA}{interface_name}")


def create_instance_uri(instance_name: str) -> URIRef:
    """Create URI for a TwinInstance"""
    return URIRef(f"{TWIN_DATA}instance/{instance_name}")


def create_property_uri(interface_name: str, property_name: str) -> URIRef:
    """Create URI for a Property"""
    return URIRef(f"{TWIN_DATA}{interface_name}/property/{property_name}")


def create_relationship_uri(interface_name: str, relationship_name: str) -> URIRef:
    """Create URI for a Relationship"""
    return URIRef(f"{TWIN_DATA}{interface_name}/relationship/{relationship_name}")


def create_command_uri(interface_name: str, command_name: str) -> URIRef:
    """Create URI for a Command"""
    return URIRef(f"{TWIN_DATA}{interface_name}/command/{command_name}")


# Location keys as they appear in YAML metadata.annotations, mapped to the
# W3C Basic Geo predicate they become. Bounds are checked where meaningful.
_LOCATION_PREDICATES = (
    ("latitude", GEO.lat, 90),
    ("longitude", GEO.long, 180),
    ("altitude", GEO.alt, None),
)


def add_location_triples(
    graph: Graph,
    subject_uri: URIRef,
    annotations: Optional[Dict[str, Any]],
) -> bool:
    """
    Write W3C Basic Geo (WGS84) location triples for a twin subject.

    Single source of truth for location→RDF mapping, shared by TwinRDFService
    (what actually reaches Fuseki) and DebugDumpService (what gets written to
    disk) so the two cannot drift apart.

    Coordinates live in YAML annotations as strings. Invalid or out-of-range
    values are skipped with a warning rather than failing the caller — one bad
    coordinate must not cost the user the whole thing.

    Args:
        graph: Target RDF graph
        subject_uri: TwinInterface or TwinInstance URI
        annotations: metadata.annotations dict from the YAML

    Returns:
        bool: True if at least one location triple was added
    """
    if not annotations:
        return False

    added = False

    for key, predicate, limit in _LOCATION_PREDICATES:
        raw = annotations.get(key)
        if raw is None or raw == "":
            continue

        try:
            value = Decimal(str(raw))
        except (InvalidOperation, ValueError):
            logger.warning(f"Skipping invalid {key} for {subject_uri}: {raw!r}")
            continue

        if limit is not None and not (-limit <= value <= limit):
            logger.warning(f"Skipping out-of-range {key} for {subject_uri}: {value}")
            continue

        graph.add((subject_uri, predicate, Literal(value, datatype=XSD.decimal)))
        added = True

    address = annotations.get("address")
    if address:
        graph.add((subject_uri, TWIN.address, Literal(address)))
        added = True

    return added


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "TWIN",
    "TS",
    "TWIN_DATA",
    "TSD",
    "GEO",
    "SOSA",
    "SSN",
    "QUDT",
    "SCHEMA",
    "ONTOLOGY_URI",
    "ONTOLOGY_VERSION",
    "RELATIONSHIP_TYPES",
    "get_twin_ontology",
    "get_cached_ontology",
    "get_relationship_types",
    "get_inverse_type_map",
    "add_location_triples",
    "create_interface_uri",
    "create_instance_uri",
    "create_property_uri",
    "create_relationship_uri",
    "create_command_uri",
]
