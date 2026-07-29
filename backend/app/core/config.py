"""
Twin-Lite Configuration

Simplified configuration without authentication, database, or Ditto settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings for Twin-Lite"""

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    # ============================================
    # APPLICATION SETTINGS
    # ============================================
    PROJECT_NAME: str = Field(default="IoDT2 Demo")
    DEBUG: bool = Field(default=False)
    API_V2_PREFIX: str = Field(default="/api/v2")
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # ============================================
    # CORS CONFIGURATION
    # ============================================
    CORS_ORIGINS: str = Field(default="*")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)

    # ============================================
    # FUSEKI TRIPLE STORE CONFIGURATION
    # ============================================
    FUSEKI_URL: str = Field(default="http://localhost:3030")
    FUSEKI_DATASET: str = Field(default="twin-db")
    FUSEKI_USERNAME: str = Field(default="admin")
    FUSEKI_PASSWORD: str = Field(default="admin")

    # Use the Jena text (Lucene) index for full text search. Off by default:
    # it requires the dataset to be configured with a text:TextDataset
    # assembler and an index build for existing data. When on, a failing text
    # query falls back to the substring scan rather than returning nothing.
    FUSEKI_TEXT_INDEX: bool = Field(default=False)

    # ============================================
    # SPARQL GUARD
    # ============================================
    # Ceiling applied to user-supplied SELECT/CONSTRUCT/DESCRIBE queries so a
    # missing LIMIT cannot pull the whole store into memory.
    SPARQL_MAX_LIMIT: int = Field(default=1000)
    # Wall clock budget for a single SPARQL request against Fuseki.
    SPARQL_TIMEOUT_SECONDS: int = Field(default=30)

    # ============================================
    # DEMO SEED
    # ============================================
    # Re-store the demo scenario even when its named graphs already exist.
    # Without this, editing a seed YAML has no effect on an environment whose
    # Fuseki volume was populated by an earlier version — the loader skips
    # anything already present.
    SEED_FORCE_RELOAD: bool = Field(default=False)

    # ============================================
    # TENANT CONFIGURATION (Simplified)
    # ============================================
    DEFAULT_TENANT_ID: str = Field(default="default")

    # ============================================
    # COMPUTED PROPERTIES
    # ============================================
    @property
    def CORS_ORIGINS_LIST(self) -> list:
        """Parse CORS origins from string to list"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
