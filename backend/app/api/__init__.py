"""
Twin-Lite API Router

Simplified API with Twin, Tenant, and DTDL endpoints.
"""

from fastapi import APIRouter
from .v2 import twin, tenants, dtdl, fuseki, ontology, discovery

# Create main API router
api_router = APIRouter()

# Include Twin routes
api_router.include_router(
    twin.router,
    prefix="/v2/twin",
    tags=["twin"]
)

# Include Tenant routes
api_router.include_router(
    tenants.router,
    prefix="/v2/tenants",
    tags=["tenants"]
)

# Include DTDL routes
api_router.include_router(
    dtdl.router,
    prefix="/v2"
)

# Include Fuseki routes (search, SPARQL, CRUD)
api_router.include_router(
    fuseki.router,
    prefix="/v2/fuseki",
    tags=["fuseki"]
)

# Include Ontology routes (published information model)
api_router.include_router(
    ontology.router,
    prefix="/v2"
)

# Include Discovery routes (geographic and capability discovery)
api_router.include_router(
    discovery.router,
    prefix="/v2"
)

# Thing Description Directory listing lives at /things per W3C WoT Discovery
api_router.include_router(
    discovery.things_router,
    prefix="/v2"
)


@api_router.get("/test")
async def test_api():
    return {"message": "Twin-Lite API is working"}
