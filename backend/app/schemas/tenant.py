"""
Tenant Schemas for TwinScale-Lite

Pydantic models for tenant CRUD operations.
Simplified without user management.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class TenantBase(BaseModel):
    tenant_id: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9-]+$")
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: bool = True
    max_things: int = Field(default=1000, ge=1, le=100000)

    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v):
        if not v or len(v) < 2:
            raise ValueError('Tenant ID must be at least 2 characters long')
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Tenant ID can only contain alphanumeric characters, hyphens, and underscores')
        return v.lower()


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    max_things: Optional[int] = Field(None, ge=1, le=100000)


class TenantInDB(TenantBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Tenant(TenantInDB):
    pass


class TenantStats(BaseModel):
    tenant_id: str
    name: str
    things_count: int = 0
    is_active: bool
    limits: dict


class TenantValidationResponse(BaseModel):
    available: bool
    message: str
