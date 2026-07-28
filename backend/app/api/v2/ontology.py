"""
Ontology API Router

Publishes the Twin ontology so external systems can consume the information
model without knowing anything about this codebase — the "open information
model" side of the platform.

- GET /ontology             RDF serialisation, content negotiated
- GET /ontology/classes     JSON summary of ts: classes and their alignments
- GET /ontology/properties  JSON summary of ts: properties
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from rdflib import Graph, RDF, RDFS, OWL, URIRef

from app.core.twin_ontology import (
    TWIN, ONTOLOGY_URI, ONTOLOGY_VERSION,
    get_cached_ontology, get_relationship_types,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ontology", tags=["ontology"])


# ============================================================================
# Serialisation formats
# ============================================================================

# media type -> rdflib serializer name. First entry is the default.
MEDIA_TYPES: Dict[str, str] = {
    "text/turtle": "turtle",
    "application/ld+json": "json-ld",
    "application/rdf+xml": "xml",
    "application/n-triples": "nt",
    # Common aliases
    "application/x-turtle": "turtle",
    "application/json": "json-ld",
    "application/xml": "xml",
    "text/n-triples": "nt",
}

DEFAULT_MEDIA_TYPE = "text/turtle"

# ?format= shorthand -> media type, for browsers and curl without headers
FORMAT_ALIASES: Dict[str, str] = {
    "turtle": "text/turtle",
    "ttl": "text/turtle",
    "jsonld": "application/ld+json",
    "json-ld": "application/ld+json",
    "json": "application/ld+json",
    "xml": "application/rdf+xml",
    "rdfxml": "application/rdf+xml",
    "rdf": "application/rdf+xml",
    "nt": "application/n-triples",
    "ntriples": "application/n-triples",
}


def _ontology() -> Graph:
    """Shared read-only ontology graph (built once, reused across requests)."""
    return get_cached_ontology()


def _negotiate(accept_header: Optional[str]) -> Optional[str]:
    """
    Pick a media type from an Accept header.

    Returns the chosen media type, or None if the client asked exclusively for
    types we cannot produce (caller should answer 406).
    """
    if not accept_header or not accept_header.strip():
        return DEFAULT_MEDIA_TYPE

    candidates: List[tuple] = []
    for part in accept_header.split(","):
        segments = part.strip().split(";")
        media = segments[0].strip().lower()
        if not media:
            continue

        quality = 1.0
        for segment in segments[1:]:
            key, _, value = segment.strip().partition("=")
            if key.strip().lower() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        candidates.append((quality, media))

    # Highest q first; ties keep the order the client listed them in
    for _, media in sorted(candidates, key=lambda c: -c[0]):
        if media in ("*/*", "application/*"):
            return DEFAULT_MEDIA_TYPE
        if media in MEDIA_TYPES:
            return media

    return None


# ============================================================================
# GET /ontology
# ============================================================================

@router.get(
    "",
    summary="Get the Twin ontology as RDF",
    description=(
        "Returns the ontology serialised according to the Accept header. "
        "Supported: text/turtle (default), application/ld+json, "
        "application/rdf+xml, application/n-triples. "
        "A ?format= query parameter overrides the header."
    ),
    response_class=Response,
    responses={
        200: {"content": {media: {} for media in MEDIA_TYPES if "/" in media}},
        406: {"description": "No supported serialisation in the Accept header"},
    },
)
async def get_ontology(
    request: Request,
    format: Optional[str] = Query(
        None,
        description="Override content negotiation: turtle, jsonld, xml or nt",
    ),
):
    if format:
        media_type = FORMAT_ALIASES.get(format.strip().lower())
        if not media_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown format '{format}'. "
                    f"Supported: {', '.join(sorted(set(FORMAT_ALIASES)))}"
                ),
            )
    else:
        media_type = _negotiate(request.headers.get("accept"))
        if media_type is None:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=(
                    "No supported serialisation requested. Supported: "
                    f"{', '.join(sorted(MEDIA_TYPES))}"
                ),
            )

    graph = _ontology()
    body = graph.serialize(format=MEDIA_TYPES[media_type])

    return Response(
        content=body,
        media_type=media_type,
        headers={
            # The ontology only changes when the code does, so the version is a
            # sound validator for caches.
            "ETag": f'"{ONTOLOGY_VERSION}"',
            "Cache-Control": "public, max-age=300",
            "X-Ontology-Version": ONTOLOGY_VERSION,
            "Vary": "Accept",
        },
    )


# ============================================================================
# JSON summaries
# ============================================================================

class TermSummary(BaseModel):
    """A single ts: class or property with its alignments."""
    uri: str = Field(description="Full URI of the term")
    curie: str = Field(description="Prefixed form, e.g. ts:TwinInterface")
    name: str = Field(description="Local name")
    label: Optional[str] = Field(None, description="rdfs:label")
    comment: Optional[str] = Field(None, description="rdfs:comment")
    parents: List[str] = Field(
        default_factory=list,
        description="rdfs:subClassOf / rdfs:subPropertyOf targets as CURIEs",
    )
    aligned_with: List[str] = Field(
        default_factory=list,
        description="Parents outside the ts: namespace — the external alignments",
    )
    see_also: List[str] = Field(default_factory=list, description="rdfs:seeAlso targets")
    domain: Optional[str] = Field(None, description="rdfs:domain (properties only)")
    range: Optional[str] = Field(None, description="rdfs:range (properties only)")


class TermListResponse(BaseModel):
    """Response wrapper for class/property listings."""
    ontology: str = Field(description="Ontology URI")
    version: str = Field(description="owl:versionInfo")
    total: int = Field(description="Number of terms returned")
    terms: List[TermSummary]


def _curie(graph: Graph, uri: URIRef) -> str:
    """Prefixed form of a URI, falling back to the full URI."""
    try:
        return graph.namespace_manager.normalizeUri(uri)
    except Exception:
        return str(uri)


def _first_literal(graph: Graph, subject: URIRef, predicate: URIRef) -> Optional[str]:
    value = graph.value(subject, predicate)
    return str(value) if value is not None else None


def _summarise(graph: Graph, subject: URIRef, hierarchy_predicate: URIRef) -> TermSummary:
    parents = list(graph.objects(subject, hierarchy_predicate))
    external = [p for p in parents if not str(p).startswith(str(TWIN))]

    domain = graph.value(subject, RDFS.domain)
    range_ = graph.value(subject, RDFS.range)

    return TermSummary(
        uri=str(subject),
        curie=_curie(graph, subject),
        name=str(subject).split("#")[-1],
        label=_first_literal(graph, subject, RDFS.label),
        comment=_first_literal(graph, subject, RDFS.comment),
        parents=[_curie(graph, p) for p in parents],
        aligned_with=[_curie(graph, p) for p in external],
        see_also=[_curie(graph, o) for o in graph.objects(subject, RDFS.seeAlso)],
        domain=_curie(graph, domain) if domain is not None else None,
        range=_curie(graph, range_) if range_ is not None else None,
    )


@router.get(
    "/classes",
    response_model=TermListResponse,
    summary="List ts: classes and their external alignments",
)
async def list_classes():
    graph = _ontology()

    subjects = {
        s for s in graph.subjects(RDF.type, RDFS.Class) if str(s).startswith(str(TWIN))
    } | {
        s for s in graph.subjects(RDF.type, OWL.Class) if str(s).startswith(str(TWIN))
    }

    terms = sorted(
        (_summarise(graph, s, RDFS.subClassOf) for s in subjects),
        key=lambda t: t.name,
    )

    return TermListResponse(
        ontology=str(ONTOLOGY_URI),
        version=ONTOLOGY_VERSION,
        total=len(terms),
        terms=terms,
    )


@router.get(
    "/properties",
    response_model=TermListResponse,
    summary="List ts: properties and their external alignments",
)
async def list_properties():
    graph = _ontology()

    # Relationship type vocabulary (ts:feeds and friends) is typed
    # owl:ObjectProperty for the owl:inverseOf pairs, but it is not part of the
    # structural property set — it is served by /relationship-types instead.
    subjects = {
        s for s in graph.subjects(RDF.type, RDF.Property) if str(s).startswith(str(TWIN))
    }

    terms = sorted(
        (_summarise(graph, s, RDFS.subPropertyOf) for s in subjects),
        key=lambda t: t.name,
    )

    return TermListResponse(
        ontology=str(ONTOLOGY_URI),
        version=ONTOLOGY_VERSION,
        total=len(terms),
        terms=terms,
    )


# ============================================================================
# Relationship type vocabulary
# ============================================================================

class RelationshipTypeInfo(BaseModel):
    """One relationship type as the ontology defines it."""
    name: str = Field(description="Local name, e.g. 'feeds'")
    uri: str = Field(description="Full URI of the type")
    label: str = Field(description="rdfs:label")
    description: str = Field(description="rdfs:comment — fallback text when no translation exists")
    inverse: Optional[str] = Field(None, description="Name of the inverse type (owl:inverseOf)")
    propagation_direction: str = Field(description="source-to-target, target-to-source or bidirectional")
    on_target_deleted: Optional[str] = Field(None, description="Policy applied when the target is deleted")
    ui_color: str = Field(description="Hex colour every UI should use for this type")
    is_derived: bool = Field(
        description="True for inverse types, which the platform generates rather than the user asserting"
    )


class RelationshipTypeListResponse(BaseModel):
    """Relationship type vocabulary, read out of the ontology."""
    ontology: str
    version: str
    total: int
    types: List[RelationshipTypeInfo]


@router.get(
    "/relationship-types",
    response_model=RelationshipTypeListResponse,
    summary="List relationship types with inverses, propagation and UI hints",
    description=(
        "The relationship type vocabulary as defined in the ontology. This is the "
        "only supported source — clients must not keep their own copy. Pass "
        "?include_derived=false to get just the types a user can assert."
    ),
)
async def list_relationship_types(
    include_derived: bool = Query(
        True,
        description="Include inverse types (isFedBy, isControlledBy, ...)",
    ),
):
    entries = get_relationship_types()
    if not include_derived:
        entries = [e for e in entries if not e["is_derived"]]

    return RelationshipTypeListResponse(
        ontology=str(ONTOLOGY_URI),
        version=ONTOLOGY_VERSION,
        total=len(entries),
        types=[RelationshipTypeInfo(**entry) for entry in entries],
    )
