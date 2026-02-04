"""
TwinScale-Lite Configuration

Simplified configuration without authentication, database, or Ditto settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings for TwinScale-Lite"""

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    # ============================================
    # APPLICATION SETTINGS
    # ============================================
    PROJECT_NAME: str = Field(default="TwinScale-Lite")
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
    FUSEKI_DATASET: str = Field(default="twinscale-db")
    FUSEKI_USERNAME: str = Field(default="admin")
    FUSEKI_PASSWORD: str = Field(default="admin")

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
