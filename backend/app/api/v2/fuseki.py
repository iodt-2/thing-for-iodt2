"""
Fuseki API Endpoints

Provides search, SPARQL query, CRUD, and health check endpoints
that wrap TwinRDFService for the frontend fusekiService.js client.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from pydantic import BaseModel

from app.services.twin_rdf_service import TwinRDFService as TwinRDFService
from app.api.dependencies import get_tenant_id
from app.core.config import get_settings
from app.core.exceptions import FusekiException
from app.core.sparql_guard import guard_query, SparqlGuardError

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

# Known SPARQL prefixes for auto-injection
_KNOWN_PREFIXES = {
    "ts:": 'PREFIX ts: <http://twin.dtd/ontology#>',
    "tsd:": 'PREFIX tsd: <http://iodt2.com/>',
    "geo:": 'PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>',
    "rdf:": 'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>',
    "rdfs:": 'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>',
    "xsd:": 'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>',
}


def _ensure_prefixes(query: str) -> str:
    """Auto-inject missing PREFIX declarations for known namespaces."""
    upper = query.upper()
    missing = []
    # Check longer prefixes first to avoid substring false positives (rdfs: before rdf:)
    sorted_prefixes = sorted(_KNOWN_PREFIXES.items(), key=lambda x: len(x[0]), reverse=True)
    for prefix_usage, prefix_decl in sorted_prefixes:
        # Use word boundary to avoid matching "rdf:" when only "rdfs:" is used
        prefix_name = prefix_usage.rstrip(":")
        pattern = rf'(?<![a-zA-Z]){re.escape(prefix_name)}:'
        if re.search(pattern, query) and prefix_decl.upper() not in upper:
            missing.append(prefix_decl)
    if missing:
        return "\n".join(missing) + "\n\n" + query
    return query


def _guard(query: str) -> str:
    """
    Run a user query through the shared SPARQL guard.

    Returns the query to execute, or raises HTTP 400 with the reason.
    """
    try:
        return guard_query(query, max_limit=settings.SPARQL_MAX_LIMIT)
    except SparqlGuardError as guard_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(guard_error),
        )


# ============================================================================
# Request/Response Models
# ============================================================================

class SparqlQueryRequest(BaseModel):
    """Request model for SPARQL query execution"""
    query: str


class SparqlPrefixResponse(BaseModel):
    """Response model for SPARQL prefixes"""
    prefixes: Dict[str, str]


# ============================================================================
# Thing CRUD Endpoints
# ============================================================================

@router.get(
    "/",
    summary="List all things",
    description="Get all TwinInterfaces and TwinInstances with pagination",
)
async def list_things(
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(10, ge=1, le=100, description="Items per page"),
    property_name: Optional[str] = Query(None, description="Filter by property name"),
    tenant_id: str = Depends(get_tenant_id),
):
    """List all things stored in Fuseki RDF."""
    try:
        rdf_service = TwinRDFService()
        result = await rdf_service.get_all_things(
            page=page,
            page_size=pageSize,
            tenant_id=tenant_id,
        )
        return result
    except FusekiException as e:
        logger.warning(f"Fuseki error listing things: {e}")
        return {"items": [], "pagination": {"page": page, "pageSize": pageSize, "total": 0}}
    except Exception as e:
        logger.warning(f"Error listing things: {e}")
        return {"items": [], "pagination": {"page": page, "pageSize": pageSize, "total": 0}}


@router.get(
    "/search/property",
    summary="Search things by property value/schema",
    description="Find TwinInterfaces that have a specific property, filtered by min/max range",
)
async def search_by_property(
    property: str = Query(..., description="Property name (e.g., temperature)"),
    operator: str = Query("gt", description="Comparison operator: gt, gte, lt, lte, eq, ne"),
    value: float = Query(0, description="Threshold value"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Search things by property schema criteria."""
    try:
        rdf_service = TwinRDFService()
        result = await rdf_service.search_by_property(
            property_name=property,
            operator=operator,
            value=value,
            tenant_id=tenant_id,
        )
        return result
    except FusekiException as e:
        logger.error(f"Property search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Property search failed: {str(e)}"
        )


@router.get(
    "/search/",
    summary="Search things",
    description="Full-text search across TwinInterfaces and TwinInstances",
)
async def search_things(
    q: str = Query(..., description="Search query string"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Search things by name, description, original ID, or property names."""
    try:
        rdf_service = TwinRDFService()
        results = await rdf_service.search(
            query=q,
            tenant_id=tenant_id,
        )
        return results
    except FusekiException as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get(
    "/health",
    summary="Fuseki health check",
    description="Check connectivity to Fuseki triplestore",
)
async def health_check():
    """Check Fuseki service health."""
    try:
        rdf_service = TwinRDFService()
        return await rdf_service.check_health()
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "detail": "Failed to connect to Fuseki service"
        }


# ============================================================================
# SPARQL Endpoints
# ============================================================================

@router.post(
    "/sparql/search",
    summary="Execute SPARQL query (search)",
    description="Execute a SPARQL SELECT query and return parsed results",
)
async def execute_sparql_search(
    request: SparqlQueryRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    """Execute a SPARQL query for search purposes."""
    try:
        query = _guard(_ensure_prefixes(request.query))

        rdf_service = TwinRDFService()
        results = await rdf_service._execute_query(query)
        parsed = rdf_service._parse_sparql_results(results)

        return parsed
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SPARQL search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SPARQL query failed: {str(e)}"
        )


@router.post(
    "/sparql",
    summary="Execute SPARQL query",
    description="Execute a SPARQL SELECT query",
)
async def execute_sparql(
    request: SparqlQueryRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    """Execute a custom read-only SPARQL query."""
    try:
        query = _guard(_ensure_prefixes(request.query))

        rdf_service = TwinRDFService()
        results = await rdf_service._execute_query(query)
        parsed = rdf_service._parse_sparql_results(results)

        return {
            "query": query,
            "results": parsed,
            "count": len(parsed)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SPARQL execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SPARQL query failed: {str(e)}"
        )


@router.get(
    "/sparql/prefixes",
    summary="Get SPARQL prefixes",
    description="Get available namespace prefixes for SPARQL queries",
)
async def get_sparql_prefixes():
    """Return available SPARQL namespace prefixes."""
    return {
        "prefixes": {
            "ts": "http://twin.dtd/ontology#",
            "tsd": "http://iodt2.com/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        }
    }


# ============================================================================
# Saved Searches (in-memory for now)
# ============================================================================

_saved_searches: List[Dict[str, Any]] = []


@router.post(
    "/saved-searches",
    summary="Save a search query",
)
async def save_search(request: dict):
    """Save a search query for later use."""
    saved = {
        "id": len(_saved_searches) + 1,
        "name": request.get("name", "Unnamed"),
        "query": request.get("query", ""),
        "isSparql": request.get("isSparql", False),
        "type": "sparql" if request.get("isSparql") else "simple",
    }
    _saved_searches.append(saved)
    return saved


# ============================================================================
# Thing Detail Endpoints (must be AFTER /search/, /health, /sparql, etc.)
# ============================================================================

@router.get(
    "/{thing_id:path}",
    summary="Get thing by ID",
    description="Get a specific thing by its URI or name",
)
async def get_thing(
    thing_id: str = Path(..., description="Thing URI or name"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a thing by its ID."""
    try:
        rdf_service = TwinRDFService()
        thing = await rdf_service.get_thing_by_id(
            thing_id=thing_id,
            tenant_id=tenant_id,
        )

        if not thing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thing '{thing_id}' not found"
            )

        return thing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get thing: {str(e)}"
        )


__all__ = ["router"]
