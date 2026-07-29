"""
Discovery API Router

Implements the W3C WoT Discovery directory role: the platform describes itself
and answers "which twins are near here" / "which twins can measure this".

Two routers live here:
  - well_known_router: GET /.well-known/wot, mounted at the site root because
    the spec fixes that path
  - router: everything under /api/v2/discovery

The self-description is generated from the routes that are actually registered
(see _affordances), so the directory can never advertise an endpoint it does
not serve.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.dependencies import get_tenant_id
from app.core.config import get_settings
from app.core.sparql_guard import guard_query, SparqlGuardError
from app.services.query_catalog_service import get_query_catalog
from app.services.thing_description_service import (
    to_thing_description, to_thing_descriptions,
)
from app.services.twin_rdf_service import TwinRDFService

logger = logging.getLogger(__name__)
settings = get_settings()

well_known_router = APIRouter(tags=["discovery"])
router = APIRouter(prefix="/discovery", tags=["discovery"])
things_router = APIRouter(prefix="/things", tags=["discovery"])

# Media type registered for Thing Descriptions by W3C WoT TD 1.1
TD_MEDIA_TYPE = "application/td+json"
TD_LIST_MEDIA_TYPE = "application/ld+json"

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ============================================================================
# Self-description (W3C WoT Discovery)
# ============================================================================

WOT_TD_CONTEXT = "https://www.w3.org/2022/wot/td/v1.1"
WOT_DISCOVERY_CONTEXT = "https://www.w3.org/2022/wot/discovery"
IODT2_CONTEXT = "http://twin.dtd/ontology#"

DIRECTORY_ID = "urn:iodt2:thing-directory"

# Affordance metadata, keyed by the FastAPI route name that provides it.
# An entry only reaches the published TD if that route exists — a stale entry
# here cannot turn into a false claim.
_AFFORDANCE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_affordance(
    route_name: str,
    *,
    kind: str,
    name: str,
    href: str,
    description: str,
    op: Optional[str] = None,
    method: str = "GET",
    content_type: str = "application/ld+json",
    uri_variables: Optional[Dict[str, Any]] = None,
    spec_defined: bool = False,
) -> None:
    """
    Declare an interaction affordance for the directory's Thing Description.

    Args:
        route_name: FastAPI route name that must exist for this to be published
        kind: "properties" or "actions"
        name: Affordance name in the TD
        href: Path relative to the API base
        description: Human readable summary
        op: WoT operation type, when the spec defines one for this affordance
        spec_defined: True when W3C WoT Discovery specifies this interaction;
            False marks it as an iodt2 extension, which the TD states openly
    """
    _AFFORDANCE_REGISTRY[route_name] = {
        "kind": kind,
        "name": name,
        "href": href,
        "description": description,
        "op": op,
        "method": method,
        "content_type": content_type,
        "uri_variables": uri_variables or {},
        "spec_defined": spec_defined,
    }


def _registered_route_names() -> set:
    """Names of the routes this module actually serves."""
    return {
        getattr(route, "name", None)
        for module_router in (router, things_router)
        for route in module_router.routes
    }


def _affordances(api_base: str) -> Dict[str, Dict[str, Any]]:
    """Build the TD affordance blocks from routes that genuinely exist."""
    live = _registered_route_names()
    blocks: Dict[str, Dict[str, Any]] = {"properties": {}, "actions": {}}

    for route_name, meta in _AFFORDANCE_REGISTRY.items():
        if route_name not in live:
            logger.warning(
                f"Affordance '{meta['name']}' declared for unknown route "
                f"'{route_name}' — leaving it out of the self-description"
            )
            continue

        form: Dict[str, Any] = {
            "href": f"{api_base}{meta['href']}",
            "htv:methodName": meta["method"],
            "contentType": meta["content_type"],
        }
        if meta["op"]:
            form["op"] = meta["op"]

        affordance: Dict[str, Any] = {
            "description": meta["description"],
            "forms": [form],
        }
        if meta["uri_variables"]:
            affordance["uriVariables"] = meta["uri_variables"]
        if not meta["spec_defined"]:
            # Say plainly which interactions are ours rather than the spec's
            affordance["ts:extension"] = True

        blocks[meta["kind"]][meta["name"]] = affordance

    return blocks


def build_self_description(base_url: str) -> Dict[str, Any]:
    """
    The directory's own Thing Description.

    Args:
        base_url: Absolute site root, e.g. http://localhost:3015
    """
    api_base = f"{base_url.rstrip('/')}/api/v2"
    blocks = _affordances(api_base)

    description = {
        "@context": [
            WOT_TD_CONTEXT,
            WOT_DISCOVERY_CONTEXT,
            {"ts": IODT2_CONTEXT, "htv": "http://www.w3.org/2011/http#"},
        ],
        "@type": "ThingDirectory",
        "id": DIRECTORY_ID,
        "title": settings.PROJECT_NAME,
        "description": (
            "Digital twin directory for the iodt2 platform. Twins are described "
            "with an ontology aligned to W3C SSN/SOSA and published as RDF."
        ),
        "version": {"instance": "1.0.0"},
        "base": f"{base_url.rstrip('/')}/",
        "securityDefinitions": {"nosec_sc": {"scheme": "nosec"}},
        "security": "nosec_sc",
        "links": [
            {
                "rel": "type",
                "href": f"{api_base}/ontology",
                "type": "text/turtle",
                "title": "Information model this directory serves",
            }
        ],
    }

    if blocks["properties"]:
        description["properties"] = blocks["properties"]
    if blocks["actions"]:
        description["actions"] = blocks["actions"]

    return description


@well_known_router.get(
    "/.well-known/wot",
    summary="Thing Directory self-description",
    description=(
        "The directory's own Thing Description, as required by W3C WoT "
        "Discovery. Interactions marked ts:extension are iodt2 additions "
        "rather than spec-defined operations."
    ),
    responses={200: {"content": {TD_MEDIA_TYPE: {}}}},
)
async def get_self_description(request: Request):
    return JSONResponse(
        content=build_self_description(str(request.base_url)),
        media_type=TD_MEDIA_TYPE,
        headers={"Cache-Control": "public, max-age=300"},
    )


# ============================================================================
# Thing Description Directory — listing and retrieval
# ============================================================================

def _api_base(request: Request) -> str:
    """Absolute API base for building hrefs, e.g. http://host/api/v2"""
    return f"{str(request.base_url).rstrip('/')}/api/v2"


def _next_link(request: Request, limit: int, offset: int, total: int) -> Optional[str]:
    """
    RFC 8288 Link value for the next page, or None on the last page.

    W3C WoT Discovery drives TDD paging through this header rather than a body
    field, so a client can walk the whole directory by following links.
    """
    next_offset = offset + limit
    if next_offset >= total:
        return None

    params = dict(request.query_params)
    params.update({"limit": str(limit), "offset": str(next_offset)})
    return f'<{request.url.path}?{urlencode(params)}>; rel="next"'


@things_router.get(
    "",
    name="list_things",
    summary="List Thing Descriptions",
    description=(
        "Returns the tenant's twins as an array of W3C WoT Thing Descriptions. "
        "Paging follows the Link header (rel=\"next\"); walking those links "
        "visits the whole directory."
    ),
    responses={200: {"content": {TD_LIST_MEDIA_TYPE: {}}}},
)
async def list_things(
    request: Request,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_tenant_id),
):
    service = TwinRDFService()

    total = await service.count_interfaces(tenant_id=tenant_id)
    uris = await service.list_interface_uris(tenant_id=tenant_id, limit=limit, offset=offset)
    records = await service.fetch_thing_records(uris, tenant_id=tenant_id)
    descriptions = to_thing_descriptions(records, _api_base(request))

    headers = {
        "X-Total-Count": str(total),
        "Content-Type": TD_LIST_MEDIA_TYPE,
    }
    next_link = _next_link(request, limit, offset, total)
    if next_link:
        headers["Link"] = next_link

    return JSONResponse(content=descriptions, media_type=TD_LIST_MEDIA_TYPE, headers=headers)


@things_router.get(
    "/{thing_name}",
    name="retrieve_thing",
    summary="Retrieve one Thing Description",
    responses={
        200: {"content": {TD_MEDIA_TYPE: {}}},
        404: {"description": "No such twin in this tenant"},
    },
)
async def retrieve_thing(
    request: Request,
    thing_name: str = Path(..., description="TwinInterface name, e.g. default-gateway1"),
    tenant_id: str = Depends(get_tenant_id),
):
    from app.core.twin_ontology import create_interface_uri

    service = TwinRDFService()
    uri = str(create_interface_uri(thing_name))
    records = await service.fetch_thing_records([uri], tenant_id=tenant_id)

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thing '{thing_name}' not found",
        )

    return JSONResponse(
        content=to_thing_description(records[0], _api_base(request)),
        media_type=TD_MEDIA_TYPE,
    )


register_affordance(
    "list_things",
    kind="properties",
    name="things",
    href="/things",
    description="Retrieve the Thing Descriptions held by this directory",
    op="readproperty",
    content_type=TD_LIST_MEDIA_TYPE,
    uri_variables={
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_PAGE_SIZE},
        "offset": {"type": "integer", "minimum": 0},
    },
    spec_defined=True,
)

register_affordance(
    "retrieve_thing",
    kind="properties",
    name="thing",
    href="/things/{name}",
    description="Retrieve a single Thing Description by name",
    op="readproperty",
    content_type=TD_MEDIA_TYPE,
    uri_variables={"name": {"type": "string"}},
    spec_defined=True,
)


# ============================================================================
# Geographic discovery
# ============================================================================

MAX_RADIUS_KM = 500.0


@router.get(
    "/nearby",
    name="discover_nearby",
    summary="Find twins near a point",
    description=(
        "Twins within radius_km of a WGS84 coordinate, nearest first. Each "
        "Thing Description carries ts:distanceKm. Twins with no recorded "
        "location cannot match. Not a W3C WoT Discovery operation — an iodt2 "
        "extension built on the geo:lat/geo:long triples in the model."
    ),
    responses={200: {"content": {TD_LIST_MEDIA_TYPE: {}}}},
)
async def discover_nearby(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude in WGS84 degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in WGS84 degrees"),
    radius_km: float = Query(1.0, gt=0, le=MAX_RADIUS_KM, description="Search radius"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    tenant_id: str = Depends(get_tenant_id),
):
    service = TwinRDFService()

    matches = await service.find_nearby(
        latitude=lat, longitude=lon, radius_km=radius_km,
        tenant_id=tenant_id, limit=limit,
    )
    if not matches:
        return JSONResponse(content=[], media_type=TD_LIST_MEDIA_TYPE,
                            headers={"X-Total-Count": "0"})

    uris = [uri for uri, _distance in matches]
    distances = dict(matches)

    records = await service.fetch_thing_records(uris, tenant_id=tenant_id)
    descriptions = to_thing_descriptions(records, _api_base(request))

    # fetch_thing_records preserves the order it was given, which is the
    # distance ordering, so the two lists line up
    for description, uri in zip(descriptions, [record["uri"] for record in records]):
        description["ts:distanceKm"] = round(distances[uri], 4)

    return JSONResponse(
        content=descriptions,
        media_type=TD_LIST_MEDIA_TYPE,
        headers={"X-Total-Count": str(len(descriptions))},
    )


register_affordance(
    "discover_nearby",
    kind="properties",
    name="nearby",
    href="/discovery/nearby",
    description="Find twins within a radius of a WGS84 coordinate",
    content_type=TD_LIST_MEDIA_TYPE,
    uri_variables={
        "lat": {"type": "number", "minimum": -90, "maximum": 90},
        "lon": {"type": "number", "minimum": -180, "maximum": 180},
        "radius_km": {"type": "number", "exclusiveMinimum": 0, "maximum": MAX_RADIUS_KM},
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_PAGE_SIZE},
    },
)


# ============================================================================
# Capability discovery
# ============================================================================

@router.get(
    "/by-capability",
    name="discover_by_capability",
    summary="Find twins by what they can measure or do",
    description=(
        "Criteria combine with AND. property matches as a case-insensitive "
        "substring; unit, thing_type and dtdl match exactly ignoring case. "
        "At least one criterion is required. An iodt2 extension, not a W3C "
        "WoT Discovery operation."
    ),
    responses={200: {"content": {TD_LIST_MEDIA_TYPE: {}}}},
)
async def discover_by_capability(
    request: Request,
    property: Optional[str] = Query(
        None, description="Property name, e.g. temperature (substring match)"
    ),
    unit: Optional[str] = Query(None, description="Unit symbol, e.g. Cel"),
    thing_type: Optional[str] = Query(None, description="atomic, composite or system"),
    dtdl: Optional[str] = Query(None, description="Bound DTMI, e.g. dtmi:iodt2:TemperatureSensor;1"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    tenant_id: str = Depends(get_tenant_id),
):
    if not any((property, unit, thing_type, dtdl)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Give at least one of: property, unit, thing_type, dtdl. "
                "Use /things to list everything."
            ),
        )

    service = TwinRDFService()
    uris = await service.find_by_capability(
        property_name=property,
        unit=unit,
        thing_type=thing_type,
        dtdl_interface=dtdl,
        tenant_id=tenant_id,
        limit=limit,
    )

    records = await service.fetch_thing_records(uris, tenant_id=tenant_id)
    descriptions = to_thing_descriptions(records, _api_base(request))

    return JSONResponse(
        content=descriptions,
        media_type=TD_LIST_MEDIA_TYPE,
        headers={"X-Total-Count": str(len(descriptions))},
    )


class CapabilityCount(BaseModel):
    name: str
    count: int
    units: List[str] = Field(default_factory=list)


class UnitCount(BaseModel):
    symbol: str
    count: int


class ThingTypeCount(BaseModel):
    name: str
    count: int


class CapabilityInventory(BaseModel):
    """What this tenant's twins actually expose — drives the discovery filters."""
    properties: List[CapabilityCount]
    units: List[UnitCount]
    thingTypes: List[ThingTypeCount]


@router.get(
    "/capabilities",
    name="list_capabilities",
    response_model=CapabilityInventory,
    summary="Inventory of measurable properties, units and twin types",
    description=(
        "Reports what is present in the store rather than a fixed list, so the "
        "discovery UI offers filters that can actually return something."
    ),
)
async def list_capabilities(tenant_id: str = Depends(get_tenant_id)):
    return await TwinRDFService().list_capabilities(tenant_id=tenant_id)


register_affordance(
    "discover_by_capability",
    kind="properties",
    name="byCapability",
    href="/discovery/by-capability",
    description="Find twins by measurable property, unit, twin type or bound DTDL interface",
    content_type=TD_LIST_MEDIA_TYPE,
    uri_variables={
        "property": {"type": "string"},
        "unit": {"type": "string"},
        "thing_type": {"type": "string"},
        "dtdl": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_PAGE_SIZE},
    },
)

register_affordance(
    "list_capabilities",
    kind="properties",
    name="capabilities",
    href="/discovery/capabilities",
    description="Inventory of properties, units and twin types present in the directory",
    content_type="application/json",
)


# ============================================================================
# SPARQL discovery profile and saved query catalog
# ============================================================================

class SavedQuery(BaseModel):
    """A saved search from the catalog."""
    id: str
    category: str
    name: str
    description: str
    query: str
    tenant_scoped: bool = Field(
        description=(
            "True when running this query restricts results to the calling "
            "tenant. False means it reads across every tenant — the searches "
            "migrated from the frontend console behave that way."
        )
    )


class QueryCatalogResponse(BaseModel):
    total: int
    categories: List[Dict[str, Any]]
    queries: List[SavedQuery]


@router.get(
    "/queries",
    name="list_saved_queries",
    response_model=QueryCatalogResponse,
    summary="Saved SPARQL searches",
    description=(
        "The saved search catalog. Lives in a data file rather than the "
        "frontend, so adding a query needs no rebuild. Every entry is parsed "
        "as SPARQL before it is served."
    ),
)
async def list_saved_queries(
    category: Optional[str] = Query(None, description="Filter by category, or 'all'"),
):
    catalog = get_query_catalog()
    queries = catalog.list_queries(category)

    return QueryCatalogResponse(
        total=len(queries),
        categories=catalog.categories(),
        queries=[SavedQuery(**entry) for entry in queries],
    )


@router.get(
    "/queries/{query_id}",
    name="get_saved_query",
    response_model=SavedQuery,
    summary="One saved search",
    responses={404: {"description": "No such saved query"}},
)
async def get_saved_query(query_id: str = Path(..., description="Catalog id")):
    entry = get_query_catalog().get_query(query_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved query '{query_id}' not found",
        )
    return SavedQuery(**entry)


@router.get(
    "/sparql",
    name="discover_sparql",
    summary="Read-only SPARQL discovery",
    description=(
        "W3C WoT Discovery's SPARQL search profile: a GET-based, read-only "
        "query endpoint. Requests pass through the same guard as the rest of "
        "the platform, so only SELECT, ASK, CONSTRUCT and DESCRIBE run and a "
        "LIMIT ceiling always applies. Pass ?saved=<id> to run a catalog entry."
    ),
    responses={400: {"description": "Query rejected by the guard"}},
)
async def discover_sparql(
    q: Optional[str] = Query(None, description="SPARQL query text"),
    saved: Optional[str] = Query(None, description="Catalog id to run instead of q"),
    tenant_id: str = Depends(get_tenant_id),
):
    tenant_scoped = False

    if saved:
        entry = get_query_catalog().render_query(saved, tenant_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Saved query '{saved}' not found",
            )
        query_text = entry["executable"]
        tenant_scoped = entry["tenant_scoped"]
        if not tenant_scoped:
            logger.info(
                f"Saved query '{saved}' carries no tenant placeholder; "
                f"results span every tenant"
            )
    elif q:
        # A hand written query is whatever the caller wrote — the platform does
        # not rewrite it, so it is not tenant scoped either
        query_text = q
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either q=<sparql> or saved=<catalog id>",
        )

    try:
        guarded = guard_query(query_text, max_limit=settings.SPARQL_MAX_LIMIT)
    except SparqlGuardError as guard_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(guard_error),
        )

    service = TwinRDFService()
    results = service._parse_sparql_results(await service._execute_query(guarded))

    return {
        "query": guarded,
        "source": f"saved:{saved}" if saved else "inline",
        # Stated rather than assumed: a query without a tenant placeholder
        # reads across every tenant, and the caller has to know that
        "tenant_scoped": tenant_scoped,
        "tenant_id": tenant_id if tenant_scoped else None,
        "count": len(results),
        "results": results,
    }


register_affordance(
    "discover_sparql",
    kind="properties",
    name="searchSPARQL",
    href="/discovery/sparql",
    description="Read-only SPARQL query over the directory",
    content_type="application/json",
    uri_variables={
        "q": {"type": "string"},
        "saved": {"type": "string"},
    },
    spec_defined=True,
)

register_affordance(
    "list_saved_queries",
    kind="properties",
    name="savedQueries",
    href="/discovery/queries",
    description="Catalog of saved SPARQL searches",
    content_type="application/json",
)
