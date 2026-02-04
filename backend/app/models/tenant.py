"""
Tenant Model for TwinScale-Lite

Simplified tenant model without user authentication.
Tenants are used to organize and isolate TwinScale things.
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), unique=True, index=True, nullable=False)  # namespace identifier
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Tenant limits
    max_things = Column(Integer, default=1000)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Tenant(tenant_id='{self.tenant_id}', name='{self.name}')>"
    
    def create_thing_id(self, device_id: str) -> str:
        """Create tenant-aware thing ID"""
        return f"{self.tenant_id}:{device_id}"
