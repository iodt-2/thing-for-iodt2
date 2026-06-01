"""
Twin-Lite API Server

Lightweight Digital Twin management system using Twin YAML format.
No Ditto, no WoT conversion - direct form-to-YAML-to-RDF workflow.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import api_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


async def ensure_fuseki_dataset():
    """Check if Fuseki dataset exists, create it and load ontology if not."""
    import httpx
    from app.core.twin_ontology import get_twin_ontology

    dataset = settings.FUSEKI_DATASET
    fuseki_url = settings.FUSEKI_URL
    auth = (settings.FUSEKI_USERNAME, settings.FUSEKI_PASSWORD)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check if dataset exists
            resp = await client.get(f"{fuseki_url}/$/datasets", auth=auth)
            if resp.status_code == 200:
                existing = [ds.get("ds.name", "").strip("/") for ds in resp.json().get("datasets", [])]
                if dataset in existing:
                    logger.info(f"Fuseki dataset '{dataset}' already exists")
                    return

            # Create dataset
            logger.info(f"Creating Fuseki dataset '{dataset}'...")
            resp = await client.post(
                f"{fuseki_url}/$/datasets",
                data={"dbName": dataset, "dbType": "tdb2"},
                auth=auth,
            )
            if resp.status_code not in [200, 201]:
                logger.error(f"Failed to create dataset: {resp.status_code} - {resp.text}")
                return
            logger.info(f"Fuseki dataset '{dataset}' created")

            # Load ontology
            logger.info("Loading Twin ontology into Fuseki...")
            ontology = get_twin_ontology()
            turtle_data = ontology.serialize(format="turtle")
            resp = await client.post(
                f"{fuseki_url}/{dataset}/data",
                content=turtle_data,
                headers={"Content-Type": "text/turtle"},
                auth=auth,
            )
            if resp.status_code in [200, 201, 204]:
                logger.info(f"Twin ontology loaded ({len(ontology)} triples)")
            else:
                logger.error(f"Failed to load ontology: {resp.status_code} - {resp.text}")

    except Exception as e:
        logger.warning(f"Could not ensure Fuseki dataset: {e}")
        logger.warning("Fuseki may not be available yet - dataset will need manual setup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("=" * 60)
    logger.info("Twin-Lite API Starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Fuseki URL: {settings.FUSEKI_URL}")
    logger.info("=" * 60)
    
    # Initialize database
    from app.core.database import init_db
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

    # Ensure Fuseki dataset exists
    await ensure_fuseki_dataset()

    # Load demo scenario
    from app.services.seed_service import load_demo_scenario
    from app.services.twin_rdf_service import TwinRDFService
    await load_demo_scenario(TwinRDFService())

    yield

    logger.info("Twin-Lite API Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Twin-Lite API",
    description="Lightweight Digital Twin management with Twin YAML format",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Twin-Lite API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3015,
        reload=settings.DEBUG
    )
