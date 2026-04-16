"""
Twin-Lite API Endpoints

Direct form-to-YAML-to-RDF workflow without WoT/Ditto dependencies.
"""
import logging
from typing import Optional, Dict, Any, Literal, List
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Path
from fastapi.responses import StreamingResponse
import io
import zipfile

from app.services.twin_generator_service import TwinGeneratorService
from app.services.twin_rdf_service import TwinRDFService
from app.services.location_service import LocationService
from app.services.debug_dump_service import DebugDumpService
from app.models.twin_models import ValidationResult
from app.api.dependencies import get_tenant_id
from pydantic import BaseModel


router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class TwinQueryRequest(BaseModel):
    """Request model for SPARQL queries"""
    query: str
    limit: Optional[int] = 100


class InterfaceListResponse(BaseModel):
    """Response model for interface list"""
    interfaces: List[Dict[str, Any]]
    count: int


class InstanceListResponse(BaseModel):
    """Response model for instance list"""
    instances: List[Dict[str, Any]]
    count: int


# ============================================================================
# Direct Creation Models (Form → Twin YAML)
# ============================================================================

class TwinPropertyInput(BaseModel):
    """Property input from form"""
    name: str
    type: Literal["float", "integer", "string", "boolean", "object", "array"] = "string"
    description: Optional[str] = None
    writable: bool = False
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    unit: Optional[str] = None


class TwinRelationshipInput(BaseModel):
    """Relationship input from form"""
    name: str
    target_interface: str
    target_instance: Optional[str] = None
    description: Optional[str] = None
    relationship_type: Optional[str] = "feeds"  # feeds, controls, contains, monitors, dependsOn


class TwinCommandInput(BaseModel):
    """Command input from form"""
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None


class TwinCreateRequest(BaseModel):
    """
    Request model for creating Twin Thing directly from form data.
    """
    # Basic info
    id: str
    name: str
    description: Optional[str] = None

    # Properties
    properties: List[TwinPropertyInput] = []

    # Relationships
    relationships: List[TwinRelationshipInput] = []

    # Location (Optional)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    altitude: Optional[float] = None

    # Commands/Actions
    commands: List[TwinCommandInput] = []

    # Service configuration (optional)
    include_service_spec: bool = True
    service_image: Optional[str] = None

    # Store options
    store_in_rdf: bool = True

    # NEW: Thing Type (Phase 1)
    thing_type: Literal["device", "sensor", "component"] = "device"

    # NEW: Domain Metadata (Phase 1)
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None

    # NEW: DTDL Integration (Phase 2)
    dtdl_interface: Optional[Dict[str, Any]] = None  # Selected DTDL interface metadata


class TwinCreateResponse(BaseModel):
    """Response model for Twin creation"""
    success: bool
    interface_name: str
    instance_name: str
    interface_yaml: str
    instance_yaml: str
    stored_in_rdf: bool
    message: str


class ValidateYamlRequest(BaseModel):
    """Request model for YAML validation"""
    yaml_content: str
    kind: Literal["TwinInterface", "TwinInstance"]


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/create",
    response_model=TwinCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Twin Thing directly from form data",
    description="Create TwinInterface and TwinInstance YAML from form input and store in RDF",
)
async def create_twin_thing(
    request: TwinCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Create Twin Thing directly from form data.

    Creates both TwinInterface (blueprint) and TwinInstance (concrete) YAML files
    and optionally stores them in Fuseki RDF database.

    Flow:
    1. Receive form data (id, name, properties, relationships, commands)
    2. Generate TwinInterface YAML
    3. Generate TwinInstance YAML
    4. Store in Fuseki RDF (if store_in_rdf=True)
    5. Return YAML content
    """
    try:
        logger.info(f"Creating Twin Thing: {request.id}")

        # Validate relationship targets exist in RDF store
        if request.relationships and request.store_in_rdf:
            rdf_service = TwinRDFService()
            invalid_targets = []
            for rel in request.relationships:
                target = rel.target_interface.strip() if rel.target_interface else ""
                if target:
                    exists = await rdf_service.interface_exists(target, tenant_id=tenant_id)
                    if not exists:
                        invalid_targets.append(target)
            if invalid_targets:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Relationship hedefleri bulunamadı: {', '.join(invalid_targets)}. "
                           f"Hedef interface'ler önce oluşturulmalıdır."
                )

        # Build thing_description dict from form data
        thing_description = {
            "@id": request.id,
            "title": request.name,
            "description": request.description,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "address": request.address,
            "altitude": request.altitude,
            "properties": {},
            "actions": {},
            "links": []
        }

        # Convert properties (deduplicate by name — first entry wins)
        seen_props: set = set()
        for prop in request.properties:
            if prop.name in seen_props:
                continue
            seen_props.add(prop.name)
            thing_description["properties"][prop.name] = {
                "type": prop.type,
                "description": prop.description,
                "writable": prop.writable,
                "minimum": prop.minimum,
                "maximum": prop.maximum,
                "unit": prop.unit
            }

        # Convert commands/actions
        for cmd in request.commands:
            thing_description["actions"][cmd.name] = {
                "description": cmd.description,
                "input": cmd.input_schema or {}
            }

        # Convert relationships to links
        for rel in request.relationships:
            rel_name = rel.name.strip() if rel.name else ""
            if not rel_name:
                target_short = rel.target_interface.split("-")[-1] if rel.target_interface else "target"
                rel_name = f"{rel.relationship_type or 'feeds'}_{target_short}"
            thing_description["links"].append({
                "rel": rel_name,
                "href": rel.target_interface,
                "title": rel.description,
                "relationship_type": rel.relationship_type or "feeds",
            })

        # Initialize generator
        generator = TwinGeneratorService()

        # Generate YAML files with new parameters
        interface_yaml = generator.generate_twin_interface_yaml(
            thing_description,
            include_service_spec=request.include_service_spec,
            thing_type=request.thing_type,
            domain_metadata={
                "manufacturer": request.manufacturer,
                "model": request.model,
                "serial_number": request.serial_number,
                "firmware_version": request.firmware_version,
            },
            tenant_id=tenant_id,
            dtdl_interface=request.dtdl_interface
        )

        instance_yaml = generator.generate_twin_instance_yaml(thing_description, tenant_id=tenant_id)

        # Get normalized names
        interface_name = generator._normalize_name(request.id, tenant_id)
        instance_name = interface_name

        # DEBUG: Tüm formatları diske yaz (ontoloji doğrulama için)
        try:
            DebugDumpService.dump(
                thing_id=request.id,
                form_data=request.model_dump(),
                interface_yaml=interface_yaml,
                instance_yaml=instance_yaml,
                metadata={
                    "tenant_id": tenant_id,
                    "name": request.name,
                    "description": request.description,
                    "thing_type": request.thing_type,
                    "manufacturer": request.manufacturer,
                    "model": request.model,
                    "serial_number": request.serial_number,
                    "firmware_version": request.firmware_version,
                    **(
                        {
                            "dtdl_interface": request.dtdl_interface.get("dtmi"),
                            "dtdl_interface_name": request.dtdl_interface.get("displayName"),
                        }
                        if request.dtdl_interface else {}
                    ),
                },
            )
        except Exception as _dbg_err:
            logger.warning(f"Debug dump failed (non-fatal): {_dbg_err}")

        # Store in RDF if requested
        stored_in_rdf = False
        if request.store_in_rdf:
            try:
                logger.info(f"Storing Twin RDF for: {request.id}")
                rdf_service = TwinRDFService()

                # Prepare metadata
                metadata = {
                    "tenant_id": tenant_id,
                    "name": request.name,
                    "description": request.description,
                    # NEW: Thing Type and Domain Metadata
                    "thing_type": request.thing_type,
                    "manufacturer": request.manufacturer,
                    "model": request.model,
                    "serial_number": request.serial_number,
                    "firmware_version": request.firmware_version,
                }

                # Add DTDL interface metadata if provided
                if request.dtdl_interface:
                    metadata["dtdl_interface"] = request.dtdl_interface.get("dtmi")
                    metadata["dtdl_interface_name"] = request.dtdl_interface.get("displayName")

                await rdf_service.store_twin_yaml(
                    interface_yaml=interface_yaml,
                    instance_yaml=instance_yaml,
                    thing_id=request.id,
                    metadata=metadata
                )
                stored_in_rdf = True
                logger.info(f"Successfully stored Twin RDF for: {request.id}")
            except Exception as rdf_error:
                logger.warning(f"Failed to store in RDF: {rdf_error}")

        return TwinCreateResponse(
            success=True,
            interface_name=interface_name,
            instance_name=instance_name,
            interface_yaml=interface_yaml,
            instance_yaml=instance_yaml,
            stored_in_rdf=stored_in_rdf,
            message=f"Twin Thing '{request.name}' created successfully"
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating Twin Thing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Twin Thing: {str(e)}"
        )


@router.get(
    "/export/{interface_name}",
    summary="Export Twin YAML as ZIP",
    description="Download TwinInterface and TwinInstance YAML files as ZIP",
)
async def export_twin_zip(
    interface_name: str = Path(..., description="Name of the TwinInterface to export"),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Export Twin YAML files from RDF as ZIP.
    """
    try:
        rdf_service = TwinRDFService()

        # Get interface details from RDF
        interface = await rdf_service.get_interface_details(interface_name, tenant_id=tenant_id)
        if not interface:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interface '{interface_name}' not found"
            )

        # Regenerate YAML from stored data
        generator = TwinGeneratorService()

        # Build thing_description from stored data
        thing_description = {
            "@id": interface.get("name", interface_name),
            "title": interface.get("name"),
            "description": interface.get("description"),
            "properties": {
                p["name"]: {
                    "type": p.get("type", "string"),
                    "description": p.get("description"),
                    "writable": p.get("writable", False)
                }
                for p in interface.get("properties", [])
            },
            "actions": {
                c["name"]: {"description": c.get("description")}
                for c in interface.get("commands", [])
            },
            "links": [
                {"rel": r["name"], "href": r.get("targetInterface", "")}
                for r in interface.get("relationships", [])
            ]
        }

        interface_yaml = generator.generate_twin_interface_yaml(thing_description, tenant_id=tenant_id)
        instance_yaml = generator.generate_twin_instance_yaml(thing_description, tenant_id=tenant_id)

        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{interface_name}_interface.yaml", interface_yaml)
            zip_file.writestr(f"{interface_name}_instance.yaml", instance_yaml)

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{interface_name}_twin.zip"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting Twin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export: {str(e)}"
        )


@router.post(
    "/validate",
    response_model=ValidationResult,
    summary="Validate Twin YAML",
    description="Validate a Twin YAML file (TwinInterface or TwinInstance)",
)
async def validate_twin_yaml(
    request: ValidateYamlRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Validate Twin YAML content.
    """
    try:
        generator = TwinGeneratorService()
        validation_result = generator.validate_twin_yaml(request.yaml_content, request.kind)
        return validation_result

    except Exception as e:
        logger.error(f"Error validating Twin YAML: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )


# ============================================================================
# RDF Query Endpoints
# ============================================================================

@router.get(
    "/rdf/interfaces",
    response_model=InterfaceListResponse,
    summary="Query Twin Interfaces from RDF",
)
async def query_interfaces(
    name_filter: Optional[str] = Query(None, description="Filter by interface name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Query TwinInterfaces from RDF database."""
    try:
        rdf_service = TwinRDFService()
        interfaces = await rdf_service.query_interfaces(
            name_filter=name_filter,
            limit=limit,
            tenant_id=tenant_id
        )

        return InterfaceListResponse(
            interfaces=interfaces,
            count=len(interfaces)
        )

    except Exception as e:
        logger.warning(f"Fuseki not available or error querying interfaces: {e}")
        # Return empty list if Fuseki is not available
        return InterfaceListResponse(
            interfaces=[],
            count=0
        )


@router.get(
    "/rdf/instances",
    response_model=InstanceListResponse,
    summary="Query Twin Instances from RDF",
)
async def query_instances(
    interface_name: Optional[str] = Query(None, description="Filter by interface"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Query TwinInstances from RDF database."""
    try:
        rdf_service = TwinRDFService()
        instances = await rdf_service.query_instances(
            interface_name=interface_name,
            limit=limit,
            tenant_id=tenant_id
        )

        return InstanceListResponse(
            instances=instances,
            count=len(instances)
        )

    except Exception as e:
        logger.warning(f"Fuseki not available or error querying instances: {e}")
        # Return empty list if Fuseki is not available
        return InstanceListResponse(
            instances=[],
            count=0
        )


@router.get(
    "/rdf/interfaces/{interface_name}",
    summary="Get Twin Interface Details",
)
async def get_interface_details(
    interface_name: str = Path(..., description="Name of the TwinInterface"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get detailed information about a TwinInterface."""
    try:
        rdf_service = TwinRDFService()
        interface = await rdf_service.get_interface_details(
            interface_name,
            tenant_id=tenant_id
        )

        if not interface:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interface '{interface_name}' not found"
            )

        return interface

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting interface details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interface details: {str(e)}"
        )


@router.get(
    "/rdf/instances/{instance_name}/relationships",
    summary="Get TwinInstance Relationships",
)
async def get_instance_relationships(
    instance_name: str = Path(..., description="Name of the TwinInstance"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get all relationships for a TwinInstance."""
    try:
        rdf_service = TwinRDFService()
        relationships = await rdf_service.get_instance_relationships(
            instance_name,
            tenant_id=tenant_id
        )

        return {
            "instance": instance_name,
            "relationships": relationships,
            "count": len(relationships)
        }

    except Exception as e:
        logger.error(f"Error getting instance relationships: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get instance relationships: {str(e)}"
        )


@router.post(
    "/rdf/query",
    summary="Execute Custom SPARQL Query",
)
async def execute_sparql_query(
    request: TwinQueryRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    """Execute a custom SPARQL SELECT query."""
    try:
        # Auto-inject missing prefixes
        query_text = request.query
        known_prefixes = {
            "ts:": 'PREFIX ts: <http://twin.dtd/ontology#>',
            "tsd:": 'PREFIX tsd: <http://iodt2.com/>',
            "rdf:": 'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>',
            "rdfs:": 'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>',
            "xsd:": 'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>',
        }
        upper = query_text.upper()
        missing = [decl for usage, decl in known_prefixes.items()
                   if usage in query_text and decl.upper() not in upper]
        if missing:
            query_text = "\n".join(missing) + "\n\n" + query_text

        # Validate SELECT (skip PREFIX lines)
        is_select = False
        for line in query_text.strip().splitlines():
            stripped = line.strip().upper()
            if not stripped or stripped.startswith("PREFIX"):
                continue
            is_select = stripped.startswith("SELECT")
            break

        if not is_select:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only SELECT queries are allowed"
            )

        rdf_service = TwinRDFService()
        results = await rdf_service._execute_query(query_text)
        parsed_results = rdf_service._parse_sparql_results(results)

        if request.limit:
            parsed_results = parsed_results[:request.limit]

        return {
            "query": request.query,
            "results": parsed_results,
            "count": len(parsed_results)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing SPARQL query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute SPARQL query: {str(e)}"
        )


@router.delete(
    "/rdf/interfaces/{interface_name}",
    summary="Delete Twin Interface from RDF",
)
async def delete_twin_interface(
    interface_name: str = Path(..., description="Name of the TwinInterface to delete"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a TwinInterface and all its instances from RDF."""
    try:
        rdf_service = TwinRDFService()
        success = await rdf_service.delete_twin(interface_name, tenant_id=tenant_id)

        if success:
            return {
                "message": f"Interface '{interface_name}' deleted successfully",
                "interface": interface_name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interface '{interface_name}' not found in tenant '{tenant_id}'"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting interface: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete interface: {str(e)}"
        )


@router.get(
    "/rdf/interfaces/{interface_name}/dependencies",
    summary="Get relationship dependencies for a TwinInterface",
)
async def get_dependencies(
    interface_name: str = Path(..., description="Name of the TwinInterface"),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get all Active relationships that reference this interface.
    Used before deletion to warn about which relationships will be deactivated.
    """
    try:
        rdf_service = TwinRDFService()
        deps = await rdf_service.get_dependencies(interface_name, tenant_id=tenant_id)
        return {
            "interface": interface_name,
            "forward_count": deps["forward_count"],
            "inverse_count": deps["inverse_count"],
            "forward_targets": deps["forward_targets"],
            "inverse_sources": deps["inverse_sources"],
        }
    except Exception as e:
        logger.error(f"Error getting dependencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dependencies: {str(e)}"
        )


@router.put(
    "/rdf/interfaces/{interface_name}/relationships/{rel_name}/reactivate",
    summary="Reactivate an Inactive relationship",
)
async def reactivate_relationship(
    interface_name: str = Path(..., description="Name of the source TwinInterface"),
    rel_name: str = Path(..., description="Name of the relationship to reactivate"),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Reactivate an Inactive relationship if the target interface exists again.
    """
    try:
        rdf_service = TwinRDFService()
        graph_filter = rdf_service._build_tenant_graph_filter(tenant_id)

        from app.core.twin_ontology import create_relationship_uri, TWIN

        rel_uri = create_relationship_uri(interface_name, rel_name)
        TS = TWIN

        # Find target of this relationship
        find_target_query = f"""
        PREFIX ts: <{TS}>
        SELECT ?targetUri WHERE {{
            GRAPH ?graph {{
                <{rel_uri}> ts:targetInterface ?targetUri .
            }}
            {graph_filter}
        }}
        """
        results = await rdf_service._execute_query(find_target_query)
        parsed = rdf_service._parse_sparql_results(results)

        if not parsed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Relationship '{rel_name}' not found on '{interface_name}'"
            )

        target_uri = parsed[0].get("targetUri", "")
        target_name = target_uri.split("/")[-1] if target_uri else ""

        # Check if target still exists
        target_exists = await rdf_service.interface_exists(target_name, tenant_id=tenant_id)
        if not target_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hedef thing '{target_name}' hala mevcut değil. Önce oluşturulmalıdır."
            )

        # Reactivate: Inactive → Active
        reactivate_query = f"""
        PREFIX ts: <{TS}>
        DELETE {{ GRAPH ?g {{ <{rel_uri}> ts:relationshipStatus ts:Inactive }} }}
        INSERT {{ GRAPH ?g {{ <{rel_uri}> ts:relationshipStatus ts:Active }} }}
        WHERE {{
            GRAPH ?g {{
                <{rel_uri}> ts:relationshipStatus ts:Inactive .
            }}
            {graph_filter}
        }}
        """
        await rdf_service._execute_update(reactivate_query)

        return {
            "message": f"Relationship '{rel_name}' reactivated successfully",
            "interface": interface_name,
            "relationship": rel_name,
            "target": target_name,
            "status": "Active",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate relationship: {str(e)}"
        )


@router.get(
    "/location",
    summary="Get location info from coordinates",
    description="Reverse geocoding and elevation lookup for coordinates",
)
async def get_location_info(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """
    Get location information (address + altitude) for given coordinates.

    Uses:
    - Nominatim (OpenStreetMap) for reverse geocoding
    - Open-Elevation API for altitude data
    """
    try:
        location_service = LocationService()
        result = await location_service.get_location_info(lat, lon)
        return result
    except Exception as e:
        logger.error(f"Error getting location info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get location info: {str(e)}"
        )


__all__ = ["router"]
