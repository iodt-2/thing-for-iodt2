"""
TwinScale Framework YAML Models
Kubernetes CRD format for TwinInterface and TwinInstance

Based on TwinScale DTD specification:
- apiVersion: dtd.twinscale/v0
- kind: TwinInterface | TwinInstance
"""
from typing import Optional, Dict, List, Any, Literal
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Common Models
# ============================================================================

class TwinScaleMetadata(BaseModel):
    """Kubernetes-style metadata for TwinScale resources"""
    name: str = Field(..., description="Unique name (ems-iodt2-<thing-name>)")
    namespace: Optional[str] = Field(None, description="Optional namespace")
    labels: Optional[Dict[str, str]] = Field(default_factory=dict)
    annotations: Optional[Dict[str, str]] = Field(default_factory=dict)

    class Config:
        extra = "allow"


# ============================================================================
# TwinInterface Models (Blueprint/Template)
# ============================================================================

class TwinScaleProperty(BaseModel):
    """Property definition in TwinInterface"""
    name: str
    type: Literal["float", "integer", "string", "boolean", "object", "array"]
    description: Optional[str] = None
    x_writable: Optional[bool] = Field(None, alias="x-writable")
    x_minimum: Optional[float] = Field(None, alias="x-minimum")
    x_maximum: Optional[float] = Field(None, alias="x-maximum")
    x_unit: Optional[str] = Field(None, alias="x-unit")

    class Config:
        populate_by_name = True
        extra = "allow"


class TwinScaleRelationship(BaseModel):
    """Relationship definition in TwinInterface"""
    name: str
    interface: str = Field(..., description="Target interface name")
    description: Optional[str] = None

    class Config:
        extra = "allow"


class TwinScaleCommand(BaseModel):
    """Command/Action definition in TwinInterface"""
    name: str
    description: Optional[str] = None
    schema_: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="schema")

    class Config:
        extra = "allow"
        populate_by_name = True


class ServiceResources(BaseModel):
    """Container resource requirements"""
    cpu: str = Field(default="500m")
    memory: str = Field(default="512Mi")


class ServiceAutoscaling(BaseModel):
    """Autoscaling configuration"""
    min: int = Field(default=1, ge=1)
    max: int = Field(default=10, ge=1)

    @field_validator("max")
    @classmethod
    def validate_max_gte_min(cls, v, info):
        if "min" in info.data and v < info.data["min"]:
            raise ValueError("max must be >= min")
        return v


class ServiceSpec(BaseModel):
    """Service container specification"""
    image: Optional[str] = Field(None, description="Container image")
    resources: Optional[ServiceResources] = Field(default_factory=ServiceResources)
    autoscaling: Optional[ServiceAutoscaling] = Field(default_factory=ServiceAutoscaling)

    class Config:
        extra = "allow"


class EventStoreSpec(BaseModel):
    """Event store configuration"""
    persistRealEvent: bool = Field(default=True)


class HistoricalStoreSpec(BaseModel):
    """Historical data store configuration"""
    persistRealEvent: bool = Field(default=True)


class TwinInterfaceSpec(BaseModel):
    """TwinInterface specification"""
    name: str = Field(..., description="Interface name (ems-iodt2-<name>)")
    properties: List[TwinScaleProperty] = Field(default_factory=list)
    relationships: List[TwinScaleRelationship] = Field(default_factory=list)
    commands: List[TwinScaleCommand] = Field(default_factory=list)
    service: Optional[ServiceSpec] = None
    eventStore: Optional[EventStoreSpec] = Field(default_factory=EventStoreSpec)
    historicalStore: Optional[HistoricalStoreSpec] = Field(default_factory=HistoricalStoreSpec)

    class Config:
        extra = "allow"


class TwinInterfaceCR(BaseModel):
    """
    TwinInterface Custom Resource (Kubernetes CRD)

    Represents a blueprint/template for a Digital Twin.
    Defines properties, relationships, commands, and service configuration.
    """
    apiVersion: str = Field(default="dtd.twinscale/v0")
    kind: Literal["TwinInterface"] = "TwinInterface"
    metadata: TwinScaleMetadata
    spec: TwinInterfaceSpec

    class Config:
        extra = "allow"


# ============================================================================
# TwinInstance Models (Concrete Instance)
# ============================================================================

class TwinInstanceRelationship(BaseModel):
    """Concrete relationship in TwinInstance"""
    name: str
    interface: str = Field(..., description="Target interface name")
    instance: str = Field(..., description="Target instance name")

    class Config:
        extra = "allow"


class TwinInstanceSpec(BaseModel):
    """TwinInstance specification"""
    name: str = Field(..., description="Instance name (ems-iodt2-<name>)")
    interface: str = Field(..., description="Reference to TwinInterface")
    twinInstanceRelationships: List[TwinInstanceRelationship] = Field(default_factory=list)

    class Config:
        extra = "allow"


class TwinInstanceCR(BaseModel):
    """
    TwinInstance Custom Resource (Kubernetes CRD)

    Represents a concrete instance of a Digital Twin.
    Links to a TwinInterface and defines specific relationships to other instances.
    """
    apiVersion: str = Field(default="dtd.twinscale/v0")
    kind: Literal["TwinInstance"] = "TwinInstance"
    metadata: TwinScaleMetadata
    spec: TwinInstanceSpec

    class Config:
        extra = "allow"


# ============================================================================
# Validation Response
# ============================================================================

class ValidationResult(BaseModel):
    """YAML validation result"""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "TwinScaleMetadata",
    "TwinScaleProperty",
    "TwinScaleRelationship",
    "TwinScaleCommand",
    "ServiceResources",
    "ServiceAutoscaling",
    "ServiceSpec",
    "EventStoreSpec",
    "HistoricalStoreSpec",
    "TwinInterfaceSpec",
    "TwinInterfaceCR",
    "TwinInstanceRelationship",
    "TwinInstanceSpec",
    "TwinInstanceCR",
    "ValidationResult",
]
