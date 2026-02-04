"""
TwinScale-Lite API Server

Lightweight Digital Twin management system using TwinScale YAML format.
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("=" * 60)
    logger.info("TwinScale-Lite API Starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Fuseki URL: {settings.FUSEKI_URL}")
    logger.info("=" * 60)
    
    # Initialize database
    from app.core.database import init_db
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

    yield

    logger.info("TwinScale-Lite API Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="TwinScale-Lite API",
    description="Lightweight Digital Twin management with TwinScale YAML format",
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
        "name": "TwinScale-Lite API",
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
