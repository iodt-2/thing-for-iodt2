"""
TwinScale Framework RDF Ontology Definition

This module defines the RDF ontology for TwinScale Framework.
It provides namespace definitions and helper functions for working with TwinScale RDF data.

Ontology URI: http://twinscale.dtd/ontology#
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

from rdflib import Namespace, Graph, RDF, RDFS, XSD, Literal, URIRef
from typing import Dict, Any


# ============================================================================
# Namespace Definitions
# ============================================================================

# TwinScale Ontology
TWINSCALE = Namespace("http://twinscale.dtd/ontology#")
TS = TWINSCALE  # Alias

# TwinScale Data (instances)
TWINSCALE_DATA = Namespace("http://iodt2.com/twinscale/")
TSD = TWINSCALE_DATA  # Alias

# Standard namespaces
# RDF, RDFS, XSD are imported from rdflib


# ============================================================================
# Ontology Definition
# ============================================================================

def get_twinscale_ontology() -> Graph:
    """
    Returns the TwinScale ontology as an RDF Graph.

    This ontology defines the vocabulary for describing TwinScale Framework
    interfaces and instances in RDF format.

    Returns:
        Graph: RDFLib graph containing the ontology
    """
    g = Graph()

    # Bind namespaces
    g.bind("ts", TWINSCALE)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    # ========================================================================
    # Classes
    # ========================================================================

    # TwinInterface Class
    g.add((TWINSCALE.TwinInterface, RDF.type, RDFS.Class))
    g.add((TWINSCALE.TwinInterface, RDFS.label, Literal("Twin Interface", lang="en")))
    g.add((TWINSCALE.TwinInterface, RDFS.comment,
           Literal("A blueprint or template for digital twins", lang="en")))

    # TwinInstance Class
    g.add((TWINSCALE.TwinInstance, RDF.type, RDFS.Class))
    g.add((TWINSCALE.TwinInstance, RDFS.label, Literal("Twin Instance", lang="en")))
    g.add((TWINSCALE.TwinInstance, RDFS.comment,
           Literal("A concrete instance of a digital twin", lang="en")))

    # Property Class
    g.add((TWINSCALE.Property, RDF.type, RDFS.Class))
    g.add((TWINSCALE.Property, RDFS.label, Literal("Property", lang="en")))
    g.add((TWINSCALE.Property, RDFS.comment,
           Literal("A data property of a twin interface", lang="en")))

    # Relationship Class
    g.add((TWINSCALE.Relationship, RDF.type, RDFS.Class))
    g.add((TWINSCALE.Relationship, RDFS.label, Literal("Relationship", lang="en")))
    g.add((TWINSCALE.Relationship, RDFS.comment,
           Literal("A relationship between twin interfaces", lang="en")))

    # Command Class
    g.add((TWINSCALE.Command, RDF.type, RDFS.Class))
    g.add((TWINSCALE.Command, RDFS.label, Literal("Command", lang="en")))
    g.add((TWINSCALE.Command, RDFS.comment,
           Literal("An actionable command on a twin interface", lang="en")))

    # InstanceRelationship Class
    g.add((TWINSCALE.InstanceRelationship, RDF.type, RDFS.Class))
    g.add((TWINSCALE.InstanceRelationship, RDFS.label, Literal("Instance Relationship", lang="en")))
    g.add((TWINSCALE.InstanceRelationship, RDFS.comment,
           Literal("A relationship between twin instances", lang="en")))

    # ========================================================================
    # Properties - Interface Structure
    # ========================================================================

    # hasProperty
    g.add((TWINSCALE.hasProperty, RDF.type, RDF.Property))
    g.add((TWINSCALE.hasProperty, RDFS.label, Literal("has property", lang="en")))
    g.add((TWINSCALE.hasProperty, RDFS.domain, TWINSCALE.TwinInterface))
    g.add((TWINSCALE.hasProperty, RDFS.range, TWINSCALE.Property))

    # hasRelationship
    g.add((TWINSCALE.hasRelationship, RDF.type, RDF.Property))
    g.add((TWINSCALE.hasRelationship, RDFS.label, Literal("has relationship", lang="en")))
    g.add((TWINSCALE.hasRelationship, RDFS.domain, TWINSCALE.TwinInterface))
    g.add((TWINSCALE.hasRelationship, RDFS.range, TWINSCALE.Relationship))

    # hasCommand
    g.add((TWINSCALE.hasCommand, RDF.type, RDF.Property))
    g.add((TWINSCALE.hasCommand, RDFS.label, Literal("has command", lang="en")))
    g.add((TWINSCALE.hasCommand, RDFS.domain, TWINSCALE.TwinInterface))
    g.add((TWINSCALE.hasCommand, RDFS.range, TWINSCALE.Command))

    # ========================================================================
    # Properties - Instance Structure
    # ========================================================================

    # instanceOf
    g.add((TWINSCALE.instanceOf, RDF.type, RDF.Property))
    g.add((TWINSCALE.instanceOf, RDFS.label, Literal("instance of", lang="en")))
    g.add((TWINSCALE.instanceOf, RDFS.domain, TWINSCALE.TwinInstance))
    g.add((TWINSCALE.instanceOf, RDFS.range, TWINSCALE.TwinInterface))

    # hasInstanceRelationship
    g.add((TWINSCALE.hasInstanceRelationship, RDF.type, RDF.Property))
    g.add((TWINSCALE.hasInstanceRelationship, RDFS.label, Literal("has instance relationship", lang="en")))
    g.add((TWINSCALE.hasInstanceRelationship, RDFS.domain, TWINSCALE.TwinInstance))
    g.add((TWINSCALE.hasInstanceRelationship, RDFS.range, TWINSCALE.InstanceRelationship))

    # ========================================================================
    # Properties - Metadata
    # ========================================================================

    # name
    g.add((TWINSCALE.name, RDF.type, RDF.Property))
    g.add((TWINSCALE.name, RDFS.label, Literal("name", lang="en")))
    g.add((TWINSCALE.name, RDFS.range, XSD.string))

    # description
    g.add((TWINSCALE.description, RDF.type, RDF.Property))
    g.add((TWINSCALE.description, RDFS.label, Literal("description", lang="en")))
    g.add((TWINSCALE.description, RDFS.range, XSD.string))

    # ========================================================================
    # Properties - Property Attributes
    # ========================================================================

    # propertyName
    g.add((TWINSCALE.propertyName, RDF.type, RDF.Property))
    g.add((TWINSCALE.propertyName, RDFS.domain, TWINSCALE.Property))
    g.add((TWINSCALE.propertyName, RDFS.range, XSD.string))

    # propertyType
    g.add((TWINSCALE.propertyType, RDF.type, RDF.Property))
    g.add((TWINSCALE.propertyType, RDFS.domain, TWINSCALE.Property))
    g.add((TWINSCALE.propertyType, RDFS.range, XSD.string))

    # writable
    g.add((TWINSCALE.writable, RDF.type, RDF.Property))
    g.add((TWINSCALE.writable, RDFS.domain, TWINSCALE.Property))
    g.add((TWINSCALE.writable, RDFS.range, XSD.boolean))

    # minimum
    g.add((TWINSCALE.minimum, RDF.type, RDF.Property))
    g.add((TWINSCALE.minimum, RDFS.domain, TWINSCALE.Property))

    # maximum
    g.add((TWINSCALE.maximum, RDF.type, RDF.Property))
    g.add((TWINSCALE.maximum, RDFS.domain, TWINSCALE.Property))

    # unit
    g.add((TWINSCALE.unit, RDF.type, RDF.Property))
    g.add((TWINSCALE.unit, RDFS.domain, TWINSCALE.Property))
    g.add((TWINSCALE.unit, RDFS.range, XSD.string))

    # ========================================================================
    # Properties - Relationship Attributes
    # ========================================================================

    # relationshipName
    g.add((TWINSCALE.relationshipName, RDF.type, RDF.Property))
    g.add((TWINSCALE.relationshipName, RDFS.domain, TWINSCALE.Relationship))
    g.add((TWINSCALE.relationshipName, RDFS.range, XSD.string))

    # targetInterface
    g.add((TWINSCALE.targetInterface, RDF.type, RDF.Property))
    g.add((TWINSCALE.targetInterface, RDFS.domain, TWINSCALE.Relationship))
    g.add((TWINSCALE.targetInterface, RDFS.range, XSD.string))

    # ========================================================================
    # Properties - Command Attributes
    # ========================================================================

    # commandName
    g.add((TWINSCALE.commandName, RDF.type, RDF.Property))
    g.add((TWINSCALE.commandName, RDFS.domain, TWINSCALE.Command))
    g.add((TWINSCALE.commandName, RDFS.range, XSD.string))

    # schema
    g.add((TWINSCALE.schema, RDF.type, RDF.Property))
    g.add((TWINSCALE.schema, RDFS.domain, TWINSCALE.Command))
    g.add((TWINSCALE.schema, RDFS.range, XSD.string))  # JSON string

    # ========================================================================
    # Properties - Instance Relationship Attributes
    # ========================================================================

    # targetInstance
    g.add((TWINSCALE.targetInstance, RDF.type, RDF.Property))
    g.add((TWINSCALE.targetInstance, RDFS.domain, TWINSCALE.InstanceRelationship))
    g.add((TWINSCALE.targetInstance, RDFS.range, TWINSCALE.TwinInstance))

    # ========================================================================
    # Properties - Provenance
    # ========================================================================

    # generatedBy
    g.add((TWINSCALE.generatedBy, RDF.type, RDF.Property))
    g.add((TWINSCALE.generatedBy, RDFS.label, Literal("generated by", lang="en")))
    g.add((TWINSCALE.generatedBy, RDFS.range, XSD.string))

    # generatedAt
    g.add((TWINSCALE.generatedAt, RDF.type, RDF.Property))
    g.add((TWINSCALE.generatedAt, RDFS.label, Literal("generated at", lang="en")))
    g.add((TWINSCALE.generatedAt, RDFS.range, XSD.dateTime))

    # sourceFormat
    g.add((TWINSCALE.sourceFormat, RDF.type, RDF.Property))
    g.add((TWINSCALE.sourceFormat, RDFS.label, Literal("source format", lang="en")))
    g.add((TWINSCALE.sourceFormat, RDFS.range, XSD.string))

    # originalId
    g.add((TWINSCALE.originalId, RDF.type, RDF.Property))
    g.add((TWINSCALE.originalId, RDFS.label, Literal("original ID", lang="en")))
    g.add((TWINSCALE.originalId, RDFS.range, XSD.string))

    return g


# ============================================================================
# Helper Functions
# ============================================================================

def create_interface_uri(interface_name: str) -> URIRef:
    """Create URI for a TwinInterface"""
    return URIRef(f"{TWINSCALE_DATA}{interface_name}")


def create_instance_uri(instance_name: str) -> URIRef:
    """Create URI for a TwinInstance"""
    return URIRef(f"{TWINSCALE_DATA}{instance_name}")


def create_property_uri(interface_name: str, property_name: str) -> URIRef:
    """Create URI for a Property"""
    return URIRef(f"{TWINSCALE_DATA}{interface_name}/property/{property_name}")


def create_relationship_uri(interface_name: str, relationship_name: str) -> URIRef:
    """Create URI for a Relationship"""
    return URIRef(f"{TWINSCALE_DATA}{interface_name}/relationship/{relationship_name}")


def create_command_uri(interface_name: str, command_name: str) -> URIRef:
    """Create URI for a Command"""
    return URIRef(f"{TWINSCALE_DATA}{interface_name}/command/{command_name}")


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "TWINSCALE",
    "TS",
    "TWINSCALE_DATA",
    "TSD",
    "get_twinscale_ontology",
    "create_interface_uri",
    "create_instance_uri",
    "create_property_uri",
    "create_relationship_uri",
    "create_command_uri",
]
