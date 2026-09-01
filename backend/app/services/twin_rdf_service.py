"""
Twin RDF Service

Converts Twin YAML to RDF triples and stores them in Fuseki twin-db.
Provides SPARQL query capabilities for Twin data.

Usage:
    service = TwinRDFService()
    await service.store_twin_yaml(interface_yaml, instance_yaml, thing_id)
    results = await service.query_interfaces()
"""

import json
import logging
import re
import yaml
import aiohttp
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from rdflib import Graph, Literal, URIRef, BNode, Namespace
from rdflib.namespace import RDF, RDFS, XSD

from ..core.config import get_settings
from ..core import (
    TWIN, TWIN_DATA, GEO,
    create_interface_uri, create_instance_uri,
    create_property_uri, create_relationship_uri, create_command_uri,
    get_twin_ontology, add_location_triples, get_inverse_type_map,
    add_provenance_triples, add_attribute_triples,
)
from ..core.exceptions import FusekiException
from ..core.geo import (
    bounding_box, haversine_km, is_valid_point, parse_coordinate,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Relationship type inverse map, derived from owl:inverseOf in the ontology.
# Not hand-maintained: adding a type to RELATIONSHIP_TYPES in twin_ontology.py
# is enough for it to show up here.
INVERSE_TYPE_MAP = get_inverse_type_map()


def get_inverse_type(rel_type: str) -> Optional[str]:
    """Returns the inverse relationship type, or None if unknown."""
    return INVERSE_TYPE_MAP.get(rel_type)


class TwinRDFService:
    """Service for managing Twin data in RDF format"""

    def __init__(self, username: str = None, password: str = None):
        """
        Initialize Twin RDF Service

        Args:
            username: Fuseki username (default from settings)
            password: Fuseki password (default from settings)
        """
        self.fuseki_url = settings.FUSEKI_URL
        self.dataset = settings.FUSEKI_DATASET
        self.endpoint = f"{self.fuseki_url}/{self.dataset}"
        self.query_endpoint = f"{self.endpoint}/query"
        self.update_endpoint = f"{self.endpoint}/update"
        self.data_endpoint = f"{self.endpoint}/data"

        self.username = username or settings.FUSEKI_USERNAME
        self.password = password or settings.FUSEKI_PASSWORD

        # Namespaces
        self.TS = TWIN
        self.TSD = TWIN_DATA
        self.GEO = GEO

        logger.info(f"TwinRDFService initialized with endpoint: {self.endpoint}")

    # ========================================================================
    # Public API - Store Operations
    # ========================================================================

    async def store_twin_yaml(
        self,
        interface_yaml: str,
        instance_yaml: str,
        thing_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store Twin YAML as RDF triples in Fuseki using Named Graph

        Args:
            interface_yaml: TwinInterface YAML string
            instance_yaml: TwinInstance YAML string
            thing_id: Original Thing ID for tracking (used as graph URI)
            metadata: Additional metadata (optional, should include tenant_id)

        Returns:
            bool: True if successful

        Raises:
            FusekiException: If storage fails
        """
        try:
            # Parse YAML
            interface_data = yaml.safe_load(interface_yaml)
            instance_data = yaml.safe_load(instance_yaml)

            # Convert to RDF
            graph = Graph()
            graph.bind("ts", self.TS)
            graph.bind("tsd", self.TSD)
            graph.bind("rdf", RDF)
            graph.bind("rdfs", RDFS)
            graph.bind("xsd", XSD)
            # replace=True: rdflib ships "geo" pre-bound to GeoSPARQL; we mean WGS84 Basic Geo
            graph.bind("geo", self.GEO, replace=True)

            # Add interface triples
            self._add_interface_to_graph(graph, interface_data, metadata)

            # Add instance triples
            self._add_instance_to_graph(graph, instance_data, metadata)

            # Get tenant_id from metadata
            tenant_id = metadata.get("tenant_id", "default") if metadata else "default"

            # Create named graph URI: http://twin.io/graphs/{tenant_id}/{thing_id}
            graph_uri = f"http://twin.io/graphs/{tenant_id}/{thing_id}"

            # Store in Fuseki as Named Graph
            await self._store_named_graph(graph, graph_uri)

            # Insert inverse relationships into each target thing's named graph
            await self._insert_inverse_relationships(interface_data, tenant_id)

            logger.info(f"Successfully stored Twin RDF for thing: {thing_id} in graph: {graph_uri}")
            return True

        except Exception as e:
            logger.error(f"Failed to store Twin RDF: {str(e)}")
            raise FusekiException(f"Failed to store Twin RDF: {str(e)}")

    async def get_dependencies(self, interface_name: str, tenant_id: str = "default") -> Dict[str, Any]:
        """
        Find all Active relationships that reference this interface (forward or inverse).

        Returns dict with forward_targets, inverse_sources, total_count.
        """
        try:
            interface_uri = create_interface_uri(interface_name)
            graph_filter = self._build_tenant_graph_filter(tenant_id)

            # Forward: bu thing'in sourceInterface olduğu relationship'ler
            fwd_query = f"""
            PREFIX ts: <{self.TS}>
            SELECT DISTINCT ?relName ?targetUri ?relType ?relStatus
            WHERE {{
                GRAPH ?graph {{
                    ?rel a ts:Relationship .
                    ?rel ts:sourceInterface <{interface_uri}> .
                    ?rel ts:targetInterface ?targetUri .
                    ?rel ts:relationshipName ?relName .
                    OPTIONAL {{ ?rel ts:relationshipType ?relType }}
                    OPTIONAL {{ ?rel ts:relationshipStatus ?relStatus }}
                }}
                {graph_filter}
            }}
            """

            # Inverse: bu thing'in targetInterface olduğu relationship'ler (diğer thing'lerin graflarında)
            inv_query = f"""
            PREFIX ts: <{self.TS}>
            SELECT DISTINCT ?relName ?sourceUri ?relType ?relStatus
            WHERE {{
                GRAPH ?graph {{
                    ?rel a ts:Relationship .
                    ?rel ts:targetInterface <{interface_uri}> .
                    ?rel ts:sourceInterface ?sourceUri .
                    ?rel ts:relationshipName ?relName .
                    OPTIONAL {{ ?rel ts:relationshipType ?relType }}
                    OPTIONAL {{ ?rel ts:relationshipStatus ?relStatus }}
                }}
                {graph_filter}
            }}
            """

            fwd_results = await self._execute_query(fwd_query)
            inv_results = await self._execute_query(inv_query)

            fwd_parsed = self._parse_sparql_results(fwd_results)
            inv_parsed = self._parse_sparql_results(inv_results)

            forward_targets = []
            for row in fwd_parsed:
                target_uri = row.get("targetUri", "")
                target_name = target_uri.split("/")[-1] if target_uri else ""
                rel_type_uri = row.get("relType", "")
                rel_status_uri = row.get("relStatus", "")
                forward_targets.append({
                    "name": target_name,
                    "type": rel_type_uri.split("#")[-1] if rel_type_uri else "",
                    "status": rel_status_uri.split("#")[-1] if rel_status_uri else "Active",
                    "relName": row.get("relName", ""),
                })

            inverse_sources = []
            for row in inv_parsed:
                source_uri = row.get("sourceUri", "")
                source_name = source_uri.split("/")[-1] if source_uri else ""
                rel_type_uri = row.get("relType", "")
                rel_status_uri = row.get("relStatus", "")
                inverse_sources.append({
                    "name": source_name,
                    "type": rel_type_uri.split("#")[-1] if rel_type_uri else "",
                    "status": rel_status_uri.split("#")[-1] if rel_status_uri else "Active",
                    "relName": row.get("relName", ""),
                })

            return {
                "forward_count": len(forward_targets),
                "inverse_count": len(inverse_sources),
                "forward_targets": forward_targets,
                "inverse_sources": inverse_sources,
            }

        except Exception as e:
            logger.error(f"Failed to get dependencies for {interface_name}: {str(e)}")
            raise FusekiException(f"Failed to get dependencies: {str(e)}")

    async def delete_twin(self, interface_name: str, tenant_id: str = "default") -> bool:
        """
        Delete Twin interface from Fuseki.

        Before dropping the graph:
        1. Deactivates all relationships in OTHER graphs that point TO this interface
           (sets ts:relationshipStatus from ts:Active to ts:Inactive)
        2. Drops this interface's own named graph (removes its forward relationships too)

        No cascade delete — other things are unaffected; only their relationship
        status changes to Inactive so historical data is preserved.

        Args:
            interface_name: Name of the TwinInterface (e.g. "iodt2-pm25")
            tenant_id: Tenant ID for graph isolation

        Returns:
            bool: True if successful
        """
        try:
            interface_uri = create_interface_uri(interface_name)
            graph_filter = self._build_tenant_graph_filter(tenant_id)

            # Step 1: Deactivate relationships in OTHER graphs that target this interface
            deactivate_query = f"""
            PREFIX ts: <{self.TS}>

            DELETE {{ GRAPH ?g {{ ?rel ts:relationshipStatus ts:Active }} }}
            INSERT {{ GRAPH ?g {{ ?rel ts:relationshipStatus ts:Inactive }} }}
            WHERE {{
                GRAPH ?g {{
                    ?rel a ts:Relationship .
                    ?rel ts:targetInterface <{interface_uri}> .
                    ?rel ts:relationshipStatus ts:Active .
                }}
                {graph_filter}
            }}
            """
            await self._execute_update(deactivate_query)
            logger.info(f"Deactivated incoming relationships pointing to: {interface_name}")

            # Step 2: Find the named graph that contains this interface
            find_query = f"""
            PREFIX ts: <{self.TS}>

            SELECT DISTINCT ?graph
            WHERE {{
                GRAPH ?graph {{
                    <{interface_uri}> a ts:TwinInterface .
                }}
                {graph_filter}
            }}
            """

            results = await self._execute_query(find_query)
            rows = self._parse_sparql_results(results)

            if not rows:
                logger.warning(f"No graph found for interface: {interface_name} (tenant: {tenant_id})")
                return False

            # Step 3: Drop the interface's own named graph
            dropped = 0
            for row in rows:
                graph_uri = row.get("graph", "")
                if not graph_uri:
                    continue
                drop_query = f"DROP SILENT GRAPH <{graph_uri}>"
                await self._execute_update(drop_query)
                logger.info(f"Dropped graph: {graph_uri}")
                dropped += 1

            logger.info(f"Deleted {dropped} graph(s) for interface: {interface_name}")
            return dropped > 0

        except Exception as e:
            logger.error(f"Failed to delete Twin data: {str(e)}")
            raise FusekiException(f"Failed to delete Twin data: {str(e)}")

    # ========================================================================
    # Public API - Query Operations
    # ========================================================================

    async def query_interfaces(
        self,
        name_filter: Optional[str] = None,
        limit: int = 100,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query all TwinInterfaces from named graphs

        Args:
            name_filter: Optional name filter (substring match)
            limit: Maximum number of results
            tenant_id: Optional tenant filter

        Returns:
            List of interface dictionaries
        """
        try:
            filter_clause = ""
            if name_filter:
                filter_clause = f'FILTER(CONTAINS(LCASE(?name), "{name_filter.lower()}"))'

            # Build tenant graph filter
            graph_filter = self._build_tenant_graph_filter(tenant_id)

            # Query across all named graphs - only TwinInterface, not TwinInstance
            query = f"""
            PREFIX ts: <{self.TS}>
            PREFIX tsd: <{self.TSD}>

            SELECT DISTINCT ?interface ?name ?description ?generatedAt ?graph
            WHERE {{
                GRAPH ?graph {{
                    ?interface a ts:TwinInterface .
                    FILTER NOT EXISTS {{ ?interface a ts:TwinInstance }}
                    ?interface ts:name ?name .
                    OPTIONAL {{ ?interface ts:description ?description }}
                    OPTIONAL {{ ?interface ts:generatedAt ?generatedAt }}
                    {filter_clause}
                }}
                {graph_filter}
            }}
            ORDER BY ?name
            LIMIT {limit}
            """

            results = await self._execute_query(query)
            return self._parse_sparql_results(results)

        except Exception as e:
            logger.error(f"Failed to query interfaces: {str(e)}")
            raise FusekiException(f"Failed to query interfaces: {str(e)}")

    async def interface_exists(
        self,
        interface_name: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if a TwinInterface exists in Fuseki for the given tenant.

        Args:
            interface_name: Name of the interface to check (e.g. "iodt2-gateway1")
            tenant_id: Tenant scope

        Returns:
            True if the interface exists, False otherwise
        """
        try:
            interface_uri = create_interface_uri(interface_name)
            graph_filter = self._build_tenant_graph_filter(tenant_id)

            query = f"""
            PREFIX ts: <{self.TS}>

            ASK {{
                GRAPH ?graph {{
                    <{interface_uri}> a ts:TwinInterface .
                }}
                {graph_filter}
            }}
            """

            results = await self._execute_query(query)
            # SPARQL ASK returns {"boolean": true/false} in JSON format
            if isinstance(results, dict):
                return results.get("boolean", False)
            return False

        except Exception as e:
            logger.warning(f"Failed to check interface existence for '{interface_name}': {e}")
            return False

    async def get_content_hash(
        self,
        thing_id: str,
        tenant_id: str = "default",
    ) -> Optional[str]:
        """
        The ts:contentHash an earlier import left on this thing's graph.

        Used to decide whether a record still matches what is stored. Storing
        replaces the whole named graph, so an unchanged record is better left
        untouched than rewritten.

        Args:
            thing_id: Original thing id, as used in the named graph URI
            tenant_id: Tenant scope

        Returns:
            The stored hash, or None when the thing or the hash is absent
        """
        graph_uri = f"http://twin.io/graphs/{tenant_id}/{thing_id}"
        query = f"""
        PREFIX ts: <{self.TS}>

        SELECT ?hash WHERE {{
            GRAPH <{graph_uri}> {{
                ?interface a ts:TwinInterface ;
                           ts:contentHash ?hash .
            }}
        }}
        LIMIT 1
        """

        try:
            results = await self._execute_query(query)
            rows = self._parse_sparql_results(results)
            return rows[0]["hash"] if rows else None
        except Exception as e:
            logger.warning(f"Failed to read content hash for '{thing_id}': {e}")
            return None

    async def query_instances(
        self,
        interface_name: Optional[str] = None,
        limit: int = 100,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query TwinInstances, optionally filtered by interface and tenant

        Args:
            interface_name: Optional interface name filter
            limit: Maximum number of results
            tenant_id: Optional tenant filter

        Returns:
            List of instance dictionaries
        """
        try:
            interface_filter = ""
            if interface_name:
                interface_uri = create_interface_uri(interface_name)
                interface_filter = f"?instance ts:instanceOf <{interface_uri}> ."

            graph_filter = self._build_tenant_graph_filter(tenant_id)

            query = f"""
            PREFIX ts: <{self.TS}>
            PREFIX tsd: <{self.TSD}>

            SELECT ?instance ?name ?interfaceName ?graph
            WHERE {{
                GRAPH ?graph {{
                    ?instance a ts:TwinInstance .
                    ?instance ts:name ?name .
                    ?instance ts:instanceOf ?interface .
                    ?interface ts:name ?interfaceName .
                    {interface_filter}
                }}
                {graph_filter}
            }}
            ORDER BY ?name
            LIMIT {limit}
            """

            results = await self._execute_query(query)
            return self._parse_sparql_results(results)

        except Exception as e:
            logger.error(f"Failed to query instances: {str(e)}")
            raise FusekiException(f"Failed to query instances: {str(e)}")

    async def get_interface_details(self, interface_name: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a TwinInterface including properties, relationships, commands

        Args:
            interface_name: Name of the interface
            tenant_id: Optional tenant filter

        Returns:
            Dictionary with interface details or None if not found
        """
        try:
            interface_uri = create_interface_uri(interface_name)

            graph_filter = self._build_tenant_graph_filter(tenant_id)

            query = f"""
            PREFIX ts: <{self.TS}>
            PREFIX tsd: <{self.TSD}>

            SELECT ?name ?description ?generatedAt ?generatedBy
                   ?propName ?propType ?propDesc ?writable
                   ?relName ?relTarget ?relDesc ?relType ?relStatus
                   ?cmdName ?cmdDesc ?graph
            WHERE {{
                GRAPH ?graph {{
                    <{interface_uri}> a ts:TwinInterface .
                    <{interface_uri}> ts:name ?name .
                    OPTIONAL {{ <{interface_uri}> ts:description ?description }}
                    OPTIONAL {{ <{interface_uri}> ts:generatedAt ?generatedAt }}
                    OPTIONAL {{ <{interface_uri}> ts:generatedBy ?generatedBy }}

                    # Properties
                    OPTIONAL {{
                        <{interface_uri}> ts:hasProperty ?prop .
                        ?prop ts:propertyName ?propName .
                        ?prop ts:propertyType ?propType .
                        OPTIONAL {{ ?prop ts:description ?propDesc }}
                        OPTIONAL {{ ?prop ts:writable ?writable }}
                    }}

                    # Relationships
                    OPTIONAL {{
                        <{interface_uri}> ts:hasRelationship ?rel .
                        ?rel ts:relationshipName ?relName .
                        ?rel ts:targetInterface ?relTarget .
                        OPTIONAL {{ ?rel ts:description ?relDesc }}
                        OPTIONAL {{ ?rel ts:relationshipType ?relType }}
                        OPTIONAL {{ ?rel ts:relationshipStatus ?relStatus }}
                    }}

                    # Commands
                    OPTIONAL {{
                        <{interface_uri}> ts:hasCommand ?cmd .
                        ?cmd ts:commandName ?cmdName .
                        OPTIONAL {{ ?cmd ts:description ?cmdDesc }}
                    }}
                }}
                {graph_filter}
            }}
            """

            results = await self._execute_query(query)
            interface = self._parse_interface_details(results)

            if interface is None:
                return None

            # Incoming relationships: bu interface'i targetInterface olarak gösteren relationship node'ları
            # hasIncomingRelationship yerine targetInterface üzerinden sorgula (Seviye 2)
            incoming_query = f"""
            PREFIX ts: <{self.TS}>
            PREFIX tsd: <{self.TSD}>

            SELECT DISTINCT ?relName ?sourceName ?sourceUri ?relDesc ?relType ?relStatus ?graph
            WHERE {{
                GRAPH ?graph {{
                    ?rel a ts:Relationship .
                    ?rel ts:targetInterface <{interface_uri}> .
                    ?rel ts:relationshipName ?relName .
                    ?rel ts:sourceInterface ?sourceUri .
                    OPTIONAL {{ ?rel ts:description ?relDesc }}
                    OPTIONAL {{ ?rel ts:relationshipType ?relType }}
                    OPTIONAL {{ ?rel ts:relationshipStatus ?relStatus }}
                    OPTIONAL {{ ?sourceUri ts:name ?sourceName }}
                }}
                {graph_filter}
            }}
            """

            incoming_results = await self._execute_query(incoming_query)
            incoming_parsed = self._parse_sparql_results(incoming_results)

            seen_incoming = set()
            incoming_relationships = []
            for row in incoming_parsed:
                source_uri = row.get("sourceUri", "")
                rel_name = row.get("relName", "")
                key = f"{source_uri}_{rel_name}"
                if key not in seen_incoming:
                    source_short = source_uri.split("/")[-1] if source_uri else ""
                    # relType URI'den son parça: http://twin.dtd/ontology#feeds → feeds
                    rel_type_uri = row.get("relType", "")
                    rel_type_short = rel_type_uri.split("#")[-1] if rel_type_uri else ""
                    rel_status_uri = row.get("relStatus", "")
                    rel_status_short = rel_status_uri.split("#")[-1] if rel_status_uri else "Active"
                    incoming_relationships.append({
                        "name": rel_name,
                        "sourceInterface": row.get("sourceName") or source_short,
                        "sourceUri": source_uri,
                        "description": row.get("relDesc"),
                        "relationshipType": rel_type_short,
                        "status": rel_status_short,
                    })
                    seen_incoming.add(key)

            interface["incomingRelationships"] = incoming_relationships
            return interface

        except Exception as e:
            logger.error(f"Failed to get interface details: {str(e)}")
            raise FusekiException(f"Failed to get interface details: {str(e)}")

    # Fields carried by the Lucene index; see fuseki/text-index.ttl
    TEXT_INDEX_FIELDS = ("name", "description", "originalId", "address")

    # Lucene query syntax characters that must be escaped in user input
    _LUCENE_SPECIAL = r'+-&|!(){}[]^"~*?:\/'

    @classmethod
    def _lucene_escape(cls, value: str) -> str:
        return "".join(
            "\\" + char if char in cls._LUCENE_SPECIAL else char
            for char in str(value)
        )

    @classmethod
    def _build_lucene_query(cls, query: str) -> str:
        """
        Turn a user search string into a Lucene query across the indexed fields.

        Every whitespace separated token must match (AND), each as a prefix so
        "temp" still finds "temperature" — matching what the substring scan did.
        """
        tokens = [cls._lucene_escape(token) for token in query.split() if token.strip()]
        if not tokens:
            return ""

        term_clause = " AND ".join(f"{token}*" for token in tokens)
        return " OR ".join(f"{field}:({term_clause})" for field in cls.TEXT_INDEX_FIELDS)

    # Probe term that must not match anything real
    _TEXT_PROBE_TERM = "iodt2zzzprobe9x7q"

    # Per-endpoint result of the text index probe; None means not yet checked
    _text_index_available: Dict[str, bool] = {}

    async def _text_query_count(self, lucene_query: str) -> int:
        """Number of subjects text:query returns for a Lucene expression."""
        probe = f"""
        PREFIX text: <http://jena.apache.org/text#>
        SELECT (COUNT(*) AS ?matches)
        WHERE {{
            GRAPH ?g {{ (?s ?score) text:query ("{self._escape_literal(lucene_query)}" 5) }}
        }}
        """
        rows = self._parse_sparql_results(await self._execute_query(probe))
        return int(rows[0].get("matches", 0)) if rows else 0

    async def _sample_indexed_term(self) -> Optional[str]:
        """
        A token that is definitely in the store, for use as a positive control.

        Names are hyphenated, and the Lucene analyser splits on hyphens, so a
        single token is taken rather than the whole name.
        """
        query = f"""
        PREFIX ts: <{self.TS}>
        SELECT ?name WHERE {{ GRAPH ?g {{ ?uri a ts:TwinInterface ; ts:name ?name }} }}
        LIMIT 1
        """
        rows = self._parse_sparql_results(await self._execute_query(query))
        if not rows:
            return None

        tokens = [t for t in re.split(r"[^A-Za-z0-9]+", rows[0].get("name", "")) if len(t) >= 3]
        return tokens[0] if tokens else None

    async def _has_working_text_index(self) -> bool:
        """
        Check that this dataset really answers text:query from an index.

        Exceptions are not a reliable signal here, in either direction:

          - With no text index configured, Jena does not raise. text:query
            matches *every* subject, so a nonsense term returns the whole
            store and search silently becomes "return everything".
          - Where text:query is not implemented at all, it quietly matches
            nothing, so search silently returns no results instead.

        Both are caught with two controls. A nonsense term must return zero,
        and a token known to be in the store must return at least one. Only
        then is the index doing real work.
        """
        cached = self._text_index_available.get(self.endpoint)
        if cached is not None:
            return cached

        available = False
        try:
            negative = await self._text_query_count(f"name:({self._TEXT_PROBE_TERM}*)")
            if negative:
                logger.error(
                    f"FUSEKI_TEXT_INDEX is on but dataset '{self.dataset}' has no "
                    f"text index: a term that cannot match returned {negative} rows. "
                    f"Falling back to the substring scan. Install "
                    f"fuseki/text-index.ttl before enabling the flag."
                )
            else:
                sample = await self._sample_indexed_term()
                if sample is None:
                    logger.info(
                        f"No indexed data in '{self.dataset}' to verify the text "
                        f"index against; using the substring scan."
                    )
                else:
                    positive = await self._text_query_count(f"name:({sample}*)")
                    available = positive > 0
                    if not available:
                        logger.error(
                            f"FUSEKI_TEXT_INDEX is on but text:query on dataset "
                            f"'{self.dataset}' matched nothing for '{sample}', which "
                            f"is present in the store. The index is missing or "
                            f"unbuilt; falling back to the substring scan."
                        )
        except Exception as exc:
            logger.warning(f"Text index probe failed for '{self.dataset}': {exc}")
            available = False

        self._text_index_available[self.endpoint] = available
        return available

    async def search(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Full text search across TwinInterfaces and TwinInstances.

        Uses the Jena text (Lucene) index when FUSEKI_TEXT_INDEX is on and the
        dataset genuinely has one; otherwise the substring scan. A dataset
        without the index configured stays fully searchable either way.
        """
        if settings.FUSEKI_TEXT_INDEX and await self._has_working_text_index():
            try:
                return await self._search_text_index(query, tenant_id, limit)
            except Exception as exc:
                logger.warning(
                    f"Text index search failed, falling back to substring scan: {exc}"
                )

        return await self._search_substring(query, tenant_id, limit)

    async def _search_text_index(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search through the Lucene index, ranked by relevance."""
        lucene_query = self._build_lucene_query(query)
        if not lucene_query:
            return []

        sparql = f"""
        PREFIX ts: <{self.TS}>
        PREFIX text: <http://jena.apache.org/text#>

        SELECT DISTINCT ?uri ?name ?type ?description ?graph ?originalId ?thingType ?score
        WHERE {{
            GRAPH ?graph {{
                (?uri ?score) text:query ("{self._escape_literal(lucene_query)}" {int(limit)}) .
                ?uri ts:name ?name .
                ?uri a ?type .
                FILTER(?type IN (ts:TwinInterface, ts:TwinInstance))
                OPTIONAL {{ ?uri ts:description ?description }}
                OPTIONAL {{ ?uri ts:originalId ?originalId }}
                OPTIONAL {{ ?uri ts:thingType ?thingType }}
            }}
            {self._build_tenant_graph_filter(tenant_id)}
        }}
        ORDER BY DESC(?score) ?name
        LIMIT {int(limit)}
        """

        parsed = self._parse_sparql_results(await self._execute_query(sparql))
        return [self._as_search_item(row) for row in parsed]

    @staticmethod
    def _as_search_item(row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise a search result row for frontend consumption."""
        return {
            "id": row.get("uri", ""),
            "name": row.get("name", ""),
            "type": "TwinInterface" if "TwinInterface" in row.get("type", "") else "TwinInstance",
            "description": row.get("description"),
            "graph": row.get("graph", ""),
            "originalId": row.get("originalId"),
            "thingType": row.get("thingType"),
        }

    async def _search_substring(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Substring scan fallback.

        Correct but unindexed: every candidate triple is read and lowercased,
        so cost grows with the store.
        """
        try:
            graph_filter = self._build_tenant_graph_filter(tenant_id)

            lc_query = self._escape_literal(query).lower()

            # Use UNION pattern to search across different fields
            # This avoids issues with OPTIONAL + FILTER interactions in Fuseki
            sparql = f"""
            PREFIX ts: <{self.TS}>
            PREFIX tsd: <{self.TSD}>

            SELECT DISTINCT ?uri ?name ?type ?description ?graph ?originalId ?thingType
            WHERE {{
                GRAPH ?graph {{
                    ?uri ts:name ?name .
                    ?uri a ?type .
                    FILTER(?type IN (ts:TwinInterface, ts:TwinInstance))
                    OPTIONAL {{ ?uri ts:description ?description }}
                    OPTIONAL {{ ?uri ts:originalId ?originalId }}
                    OPTIONAL {{ ?uri ts:thingType ?thingType }}
                }}
                {graph_filter}
                FILTER(
                    CONTAINS(LCASE(STR(?name)), "{lc_query}")
                    || CONTAINS(LCASE(STR(?graph)), "{lc_query}")
                    || (BOUND(?description) && CONTAINS(LCASE(STR(?description)), "{lc_query}"))
                    || (BOUND(?originalId) && CONTAINS(LCASE(STR(?originalId)), "{lc_query}"))
                )
            }}
            ORDER BY ?name
            LIMIT {limit}
            """

            results = await self._execute_query(sparql)
            parsed = self._parse_sparql_results(results)

            return [self._as_search_item(row) for row in parsed]

        except Exception as e:
            logger.error(f"Failed to search: {str(e)}")
            raise FusekiException(f"Failed to search: {str(e)}")

    # ========================================================================
    # Public API - Discovery
    # ========================================================================

    async def count_interfaces(self, tenant_id: Optional[str] = None) -> int:
        """Total number of TwinInterfaces visible to a tenant."""
        query = f"""
        PREFIX ts: <{self.TS}>
        SELECT (COUNT(DISTINCT ?uri) AS ?total)
        WHERE {{
            GRAPH ?graph {{ ?uri a ts:TwinInterface }}
            {self._build_tenant_graph_filter(tenant_id)}
        }}
        """
        rows = self._parse_sparql_results(await self._execute_query(query))
        return int(rows[0]["total"]) if rows else 0

    async def list_interface_uris(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[str]:
        """
        One page of TwinInterface URIs, ordered by name.

        Paging happens here rather than on the detail query: properties,
        commands and relationships multiply the rows, so a LIMIT applied to
        that result would cut a thing in half.
        """
        query = f"""
        PREFIX ts: <{self.TS}>
        SELECT DISTINCT ?uri ?name
        WHERE {{
            GRAPH ?graph {{
                ?uri a ts:TwinInterface .
                ?uri ts:name ?name .
            }}
            {self._build_tenant_graph_filter(tenant_id)}
        }}
        ORDER BY ?name
        OFFSET {int(offset)}
        LIMIT {int(limit)}
        """
        rows = self._parse_sparql_results(await self._execute_query(query))
        return [row["uri"] for row in rows if row.get("uri")]

    async def fetch_thing_records(
        self,
        uris: List[str],
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Everything needed to describe the given TwinInterfaces, grouped per thing.

        Returns records in the order the URIs were given, each with metadata,
        location, properties, commands and outgoing relationships.
        """
        if not uris:
            return []

        values = " ".join(f"<{uri}>" for uri in uris)
        query = f"""
        PREFIX ts: <{self.TS}>
        PREFIX geo: <{self.GEO}>

        SELECT ?uri ?name ?description ?thingType ?originalId
               ?manufacturer ?model ?serialNumber ?firmwareVersion
               ?dtdlInterface ?dtdlCategory
               ?lat ?lon ?alt ?address
               ?propName ?propType ?propDesc ?propUnit ?writable ?minimum ?maximum
               ?cmdName ?cmdDesc
               ?relName ?relTarget ?relType ?relStatus
        WHERE {{
            VALUES ?uri {{ {values} }}
            GRAPH ?graph {{
                ?uri a ts:TwinInterface .
                ?uri ts:name ?name .
                OPTIONAL {{ ?uri ts:description ?description }}
                OPTIONAL {{ ?uri ts:thingType ?thingType }}
                OPTIONAL {{ ?uri ts:originalId ?originalId }}
                OPTIONAL {{ ?uri ts:manufacturer ?manufacturer }}
                OPTIONAL {{ ?uri ts:model ?model }}
                OPTIONAL {{ ?uri ts:serialNumber ?serialNumber }}
                OPTIONAL {{ ?uri ts:firmwareVersion ?firmwareVersion }}
                OPTIONAL {{ ?uri ts:dtdlInterface ?dtdlInterface }}
                OPTIONAL {{ ?uri ts:dtdlCategory ?dtdlCategory }}
                OPTIONAL {{ ?uri geo:lat ?lat }}
                OPTIONAL {{ ?uri geo:long ?lon }}
                OPTIONAL {{ ?uri geo:alt ?alt }}
                OPTIONAL {{ ?uri ts:address ?address }}
                OPTIONAL {{
                    ?uri ts:hasProperty ?prop .
                    ?prop ts:propertyName ?propName .
                    OPTIONAL {{ ?prop ts:propertyType ?propType }}
                    OPTIONAL {{ ?prop ts:description ?propDesc }}
                    OPTIONAL {{ ?prop ts:unit ?propUnit }}
                    OPTIONAL {{ ?prop ts:writable ?writable }}
                    OPTIONAL {{ ?prop ts:minimum ?minimum }}
                    OPTIONAL {{ ?prop ts:maximum ?maximum }}
                }}
                OPTIONAL {{
                    ?uri ts:hasCommand ?cmd .
                    ?cmd ts:commandName ?cmdName .
                    OPTIONAL {{ ?cmd ts:description ?cmdDesc }}
                }}
                OPTIONAL {{
                    ?uri ts:hasRelationship ?rel .
                    ?rel ts:relationshipName ?relName .
                    ?rel ts:targetInterface ?relTarget .
                    OPTIONAL {{ ?rel ts:relationshipType ?relType }}
                    OPTIONAL {{ ?rel ts:relationshipStatus ?relStatus }}
                }}
            }}
            {self._build_tenant_graph_filter(tenant_id)}
        }}
        """
        rows = self._parse_sparql_results(await self._execute_query(query))
        return self._group_thing_records(rows, uris)

    @staticmethod
    def _escape_literal(value: str) -> str:
        """
        Escape a user supplied value for use inside a double-quoted SPARQL literal.

        Queries are assembled as text, so anything reaching a literal has to be
        escaped here — a stray quote or newline would otherwise close the
        literal and let the rest of the input be read as query syntax.

        The single quote is deliberately left alone. It needs no escaping inside
        a double-quoted literal, and although SPARQL 1.1 permits \\' as an ECHAR,
        rdflib's parser rejects it — so escaping it would break any search for a
        value containing an apostrophe.
        """
        return (
            str(value)
            .replace("\\", "\\\\")   # must come first
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )

    async def find_by_capability(
        self,
        property_name: Optional[str] = None,
        unit: Optional[str] = None,
        thing_type: Optional[str] = None,
        dtdl_interface: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[str]:
        """
        TwinInterfaces matching capability criteria, combined with AND.

        property_name matches as a case-insensitive substring, so "temp" finds
        "temperature". unit, thing_type and dtdl_interface match exactly,
        ignoring case — a unit symbol is an identifier, not a search term.
        """
        conditions: List[str] = []
        needs_property = bool(property_name or unit)

        if needs_property:
            conditions.append(
                "?uri ts:hasProperty ?prop . ?prop ts:propertyName ?propName ."
            )
        if unit:
            conditions.append("?prop ts:unit ?unit .")
        if thing_type:
            conditions.append("?uri ts:thingType ?thingType .")
        if dtdl_interface:
            conditions.append("?uri ts:dtdlInterface ?dtdl .")

        filters: List[str] = []
        if property_name:
            filters.append(
                f'FILTER(CONTAINS(LCASE(STR(?propName)), "{self._escape_literal(property_name).lower()}"))'
            )
        if unit:
            filters.append(
                f'FILTER(LCASE(STR(?unit)) = "{self._escape_literal(unit).lower()}")'
            )
        if thing_type:
            filters.append(
                f'FILTER(LCASE(STR(?thingType)) = "{self._escape_literal(thing_type).lower()}")'
            )
        if dtdl_interface:
            filters.append(
                f'FILTER(LCASE(STR(?dtdl)) = "{self._escape_literal(dtdl_interface).lower()}")'
            )

        query = f"""
        PREFIX ts: <{self.TS}>

        SELECT DISTINCT ?uri ?name
        WHERE {{
            GRAPH ?graph {{
                ?uri a ts:TwinInterface .
                ?uri ts:name ?name .
                {chr(10).join(conditions)}
            }}
            {self._build_tenant_graph_filter(tenant_id)}
            {chr(10).join(filters)}
        }}
        ORDER BY ?name
        LIMIT {int(limit)}
        """

        rows = self._parse_sparql_results(await self._execute_query(query))
        return [row["uri"] for row in rows if row.get("uri")]

    async def list_capabilities(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Inventory of what the tenant's twins can actually measure or do.

        Feeds the discovery UI's filter options, so it reports what is really
        present rather than a fixed list.
        """
        graph_filter = self._build_tenant_graph_filter(tenant_id)

        property_query = f"""
        PREFIX ts: <{self.TS}>

        SELECT ?propName ?unit (COUNT(DISTINCT ?uri) AS ?count)
        WHERE {{
            GRAPH ?graph {{
                ?uri a ts:TwinInterface .
                ?uri ts:hasProperty ?prop .
                ?prop ts:propertyName ?propName .
                OPTIONAL {{ ?prop ts:unit ?unit }}
            }}
            {graph_filter}
        }}
        GROUP BY ?propName ?unit
        ORDER BY ?propName
        """

        type_query = f"""
        PREFIX ts: <{self.TS}>

        SELECT ?thingType (COUNT(DISTINCT ?uri) AS ?count)
        WHERE {{
            GRAPH ?graph {{
                ?uri a ts:TwinInterface .
                ?uri ts:thingType ?thingType .
            }}
            {graph_filter}
        }}
        GROUP BY ?thingType
        ORDER BY ?thingType
        """

        property_rows = self._parse_sparql_results(await self._execute_query(property_query))
        type_rows = self._parse_sparql_results(await self._execute_query(type_query))

        properties: Dict[str, Dict[str, Any]] = {}
        units: Dict[str, int] = {}

        for row in property_rows:
            name = row.get("propName")
            if not name:
                continue

            count = int(row.get("count") or 0)
            entry = properties.setdefault(name, {"name": name, "count": 0, "units": []})
            entry["count"] += count

            unit = row.get("unit")
            if unit:
                if unit not in entry["units"]:
                    entry["units"].append(unit)
                units[unit] = units.get(unit, 0) + count

        return {
            "properties": sorted(properties.values(), key=lambda item: item["name"]),
            "units": [
                {"symbol": symbol, "count": count}
                for symbol, count in sorted(units.items())
            ],
            "thingTypes": [
                {"name": row["thingType"], "count": int(row.get("count") or 0)}
                for row in type_rows
                if row.get("thingType")
            ],
        }

    async def find_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        tenant_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Tuple[str, float]]:
        """
        TwinInterfaces within radius_km of a point, nearest first.

        Two stages: a bounding-box filter in SPARQL to avoid pulling every
        located twin, then an exact haversine pass in Python. The box is only
        an optimisation — it is allowed to be loose, never tight.

        Twins without usable coordinates simply do not match.

        Returns:
            (interface URI, distance in km) pairs, closest first
        """
        bounds = bounding_box(latitude, longitude, radius_km)

        filters = [
            f"FILTER(?lat >= {bounds['min_lat']:.10f} && ?lat <= {bounds['max_lat']:.10f})"
        ]
        if bounds["min_lon"] is not None and bounds["max_lon"] is not None:
            filters.append(
                f"FILTER(?lon >= {bounds['min_lon']:.10f} && ?lon <= {bounds['max_lon']:.10f})"
            )
        else:
            logger.debug(
                "Longitude pre-filter skipped (pole or antimeridian); "
                "haversine still applies the exact bound"
            )

        query = f"""
        PREFIX ts: <{self.TS}>
        PREFIX geo: <{self.GEO}>

        SELECT ?uri ?lat ?lon
        WHERE {{
            GRAPH ?graph {{
                ?uri a ts:TwinInterface .
                ?uri geo:lat ?lat .
                ?uri geo:long ?lon .
            }}
            {self._build_tenant_graph_filter(tenant_id)}
            {chr(10).join(filters)}
        }}
        """

        rows = self._parse_sparql_results(await self._execute_query(query))

        matches: List[Tuple[str, float]] = []
        for row in rows:
            lat = parse_coordinate(row.get("lat"))
            lon = parse_coordinate(row.get("lon"))
            if not is_valid_point(lat, lon):
                continue

            distance = haversine_km(latitude, longitude, lat, lon)
            if distance <= radius_km:
                matches.append((row["uri"], distance))

        matches.sort(key=lambda match: match[1])
        return matches[:limit]

    # ========================================================================
    # Impact analysis support
    # ========================================================================

    async def list_located_interfaces(
        self,
        tenant_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Twins that carry coordinates, with the structural type they declare.

        This is what a hazard simulation needs from us: where each twin is and
        what kind of structure it is. Twins without coordinates cannot be
        placed in a ground-motion field and are left out.

        Returns:
            Dicts with name, uri, latitude, longitude and structure_type
        """
        query = f"""
        PREFIX ts: <{self.TS}>
        PREFIX geo: <{self.GEO}>

        SELECT ?uri ?name ?lat ?lon ?structure
        WHERE {{
            GRAPH ?graph {{
                ?uri a ts:TwinInterface ;
                     ts:name ?name ;
                     geo:lat ?lat ;
                     geo:long ?lon .
                OPTIONAL {{
                    ?uri ts:hasAttribute ?attribute .
                    ?attribute ts:attributeName "buildingType" ;
                               ts:attributeValue ?structure .
                }}
            }}
            {self._build_tenant_graph_filter(tenant_id)}
        }}
        """

        rows = self._parse_sparql_results(await self._execute_query(query))

        located: List[Dict[str, Any]] = []
        for row in rows:
            latitude = parse_coordinate(row.get("lat"))
            longitude = parse_coordinate(row.get("lon"))
            if not is_valid_point(latitude, longitude):
                continue
            located.append({
                "uri": row.get("uri"),
                "name": row.get("name"),
                "latitude": latitude,
                "longitude": longitude,
                "structure_type": row.get("structure"),
            })

        located.sort(key=lambda item: item["name"] or "")
        return located[:limit] if limit else located

    async def list_relationship_edges(
        self,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Every relationship in the tenant, as source/target/type triples.

        Both the asserted relationships and the inverses the platform wrote
        come back; impact analysis collapses the duplicate hops itself.

        Returns:
            Dicts with uri, name, source, target, type and status
        """
        query = f"""
        PREFIX ts: <{self.TS}>

        SELECT ?rel ?name ?source ?target ?type ?status
        WHERE {{
            GRAPH ?graph {{
                ?rel a ts:Relationship ;
                     ts:sourceInterface ?source ;
                     ts:targetInterface ?target .
                OPTIONAL {{ ?rel ts:relationshipName ?name }}
                OPTIONAL {{ ?rel ts:relationshipType ?type }}
                OPTIONAL {{ ?rel ts:relationshipStatus ?status }}
            }}
            {self._build_tenant_graph_filter(tenant_id)}
        }}
        """

        rows = self._parse_sparql_results(await self._execute_query(query))
        return [
            {
                "uri": row.get("rel"),
                "name": row.get("name"),
                "source": self._local_name(row.get("source")),
                "target": self._local_name(row.get("target")),
                "type": self._local_name(row.get("type")),
                "status": self._local_name(row.get("status")),
            }
            for row in rows
        ]

    async def set_relationship_status(
        self,
        relationship_uris: List[str],
        status: str = "Degraded",
        tenant_id: Optional[str] = None,
    ) -> int:
        """
        Mark relationships with a status, replacing whatever they carried.

        Relationships are never deleted to record a failure — the platform
        changes their status so the history stays readable, the same rule the
        delete path follows.

        Args:
            relationship_uris: reified ts:Relationship nodes to update
            status: local name of a ts:RelationshipStatus individual
            tenant_id: tenant scope, so one tenant cannot degrade another's graph

        Returns:
            Number of relationships the update was issued for
        """
        if not relationship_uris:
            return 0

        values = " ".join(f"<{uri}>" for uri in relationship_uris)
        status_uri = self.TS[status]
        graph_filter = self._build_tenant_graph_filter(tenant_id)

        update = f"""
        PREFIX ts: <{self.TS}>

        DELETE {{ GRAPH ?graph {{ ?rel ts:relationshipStatus ?old }} }}
        INSERT {{ GRAPH ?graph {{ ?rel ts:relationshipStatus <{status_uri}> }} }}
        WHERE {{
            GRAPH ?graph {{
                ?rel a ts:Relationship .
                OPTIONAL {{ ?rel ts:relationshipStatus ?old }}
            }}
            VALUES ?rel {{ {values} }}
            {graph_filter}
        }}
        """

        await self._execute_update(update)
        effective_tenant = tenant_id or "default"
        logger.info(
            f"Set status '{status}' on {len(relationship_uris)} relationship(s) "
            f"for tenant '{effective_tenant}'"
        )
        return len(relationship_uris)

    async def list_simulation_runs(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Simulation runs recorded for a tenant, newest first.

        Runs live in their own named graphs, so listing them cannot disturb or
        be disturbed by the twins they are about.
        """
        query = f"""
        PREFIX ts: <{self.TS}>
        PREFIX geo: <{self.GEO}>

        SELECT ?runId ?at ?hazard ?magnitude ?lat ?lon (COUNT(?impact) AS ?impacts)
        WHERE {{
            GRAPH ?graph {{
                ?run a ts:SimulationRun ;
                     ts:runId ?runId .
                OPTIONAL {{ ?run ts:simulatedAt ?at }}
                OPTIONAL {{ ?run ts:hazardType ?hazard }}
                OPTIONAL {{ ?run ts:magnitude ?magnitude }}
                OPTIONAL {{ ?run geo:lat ?lat }}
                OPTIONAL {{ ?run geo:long ?lon }}
                OPTIONAL {{ ?run ts:hasImpact ?impact }}
            }}
            {self._build_tenant_graph_filter(tenant_id)}
        }}
        GROUP BY ?runId ?at ?hazard ?magnitude ?lat ?lon
        """

        rows = self._parse_sparql_results(await self._execute_query(query))
        runs = [
            {
                "run_id": row.get("runId"),
                "simulated_at": row.get("at"),
                "hazard": row.get("hazard"),
                "magnitude": parse_coordinate(row.get("magnitude")),
                "latitude": parse_coordinate(row.get("lat")),
                "longitude": parse_coordinate(row.get("lon")),
                "impacts": int(row.get("impacts") or 0),
            }
            for row in rows
        ]
        runs.sort(key=lambda run: run.get("simulated_at") or "", reverse=True)
        return runs[:limit]

    async def get_simulation_run(
        self,
        run_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        One run with the impacts it recorded, or None when there is no such run.
        """
        tenant = tenant_id or "default"
        graph_uri = f"http://twin.io/graphs/{tenant}/simulation/{run_id}"

        query = f"""
        PREFIX ts: <{self.TS}>
        PREFIX geo: <{self.GEO}>

        SELECT ?at ?hazard ?magnitude ?depth ?lat ?lon ?source
               ?impact ?kind ?subject ?severity ?state ?pga ?distance
               ?depthHops ?from ?via
        WHERE {{
            GRAPH <{graph_uri}> {{
                ?run a ts:SimulationRun ;
                     ts:runId "{self._escape_literal(run_id)}" .
                OPTIONAL {{ ?run ts:simulatedAt ?at }}
                OPTIONAL {{ ?run ts:hazardType ?hazard }}
                OPTIONAL {{ ?run ts:magnitude ?magnitude }}
                OPTIONAL {{ ?run ts:depthKm ?depth }}
                OPTIONAL {{ ?run geo:lat ?lat }}
                OPTIONAL {{ ?run geo:long ?lon }}
                OPTIONAL {{ ?run ts:externalSource ?source }}
                OPTIONAL {{
                    ?run ts:hasImpact ?impact .
                    ?impact ts:impactKind ?kind ;
                            ts:impactSubject ?subject ;
                            ts:severity ?severity .
                    OPTIONAL {{ ?impact ts:damageState ?state }}
                    OPTIONAL {{ ?impact ts:peakGroundAcceleration ?pga }}
                    OPTIONAL {{ ?impact ts:distanceKm ?distance }}
                    OPTIONAL {{ ?impact ts:propagationDepth ?depthHops }}
                    OPTIONAL {{ ?impact ts:propagatedFrom ?from }}
                    OPTIONAL {{ ?impact ts:viaRelationshipType ?via }}
                }}
            }}
        }}
        """

        rows = self._parse_sparql_results(await self._execute_query(query))
        if not rows:
            return None

        head = rows[0]
        run: Dict[str, Any] = {
            "run_id": run_id,
            "simulated_at": head.get("at"),
            "hazard": head.get("hazard"),
            "magnitude": parse_coordinate(head.get("magnitude")),
            "depth_km": parse_coordinate(head.get("depth")),
            "latitude": parse_coordinate(head.get("lat")),
            "longitude": parse_coordinate(head.get("lon")),
            "provider": head.get("source"),
            "direct": [],
            "propagated": [],
        }

        for row in rows:
            if not row.get("impact"):
                continue
            entry = {
                "thing": self._local_name(row.get("subject")),
                "severity": parse_coordinate(row.get("severity")),
            }
            if self._local_name(row.get("kind")) == "PropagatedImpact":
                entry["depth"] = int(float(row.get("depthHops") or 0))
                entry["via_thing"] = self._local_name(row.get("from"))
                entry["via_type"] = self._local_name(row.get("via"))
                run["propagated"].append(entry)
            else:
                entry["damage_state"] = row.get("state")
                entry["pga"] = parse_coordinate(row.get("pga"))
                entry["distance_km"] = parse_coordinate(row.get("distance"))
                run["direct"].append(entry)

        run["direct"].sort(key=lambda item: -(item.get("severity") or 0))
        run["propagated"].sort(key=lambda item: -(item.get("severity") or 0))
        return run

    async def store_graph_at(self, graph: Graph, graph_uri: str) -> bool:
        """
        Replace one named graph with the given triples.

        Used for graphs the platform owns outright, such as a simulation run.
        """
        await self._store_named_graph(graph, graph_uri)
        return True

    @staticmethod
    def _local_name(value: Optional[str]) -> Optional[str]:
        """Last path or fragment segment of a URI; passes plain strings through."""
        if not value:
            return value
        return value.rsplit("#", 1)[-1].rsplit("/", 1)[-1]

    def _group_thing_records(
        self,
        rows: List[Dict[str, Any]],
        uris: List[str],
    ) -> List[Dict[str, Any]]:
        """Collapse the cross-product returned by the detail query into things."""
        records: Dict[str, Dict[str, Any]] = {}

        for row in rows:
            uri = row.get("uri")
            if not uri:
                continue

            record = records.get(uri)
            if record is None:
                record = {
                    "uri": uri,
                    "name": row.get("name"),
                    "description": row.get("description"),
                    "thingType": row.get("thingType"),
                    "originalId": row.get("originalId"),
                    "manufacturer": row.get("manufacturer"),
                    "model": row.get("model"),
                    "serialNumber": row.get("serialNumber"),
                    "firmwareVersion": row.get("firmwareVersion"),
                    "dtdlInterface": row.get("dtdlInterface"),
                    "dtdlCategory": row.get("dtdlCategory"),
                    "latitude": row.get("lat"),
                    "longitude": row.get("lon"),
                    "altitude": row.get("alt"),
                    "address": row.get("address"),
                    "properties": {},
                    "commands": {},
                    "relationships": {},
                }
                records[uri] = record

            prop_name = row.get("propName")
            if prop_name and prop_name not in record["properties"]:
                record["properties"][prop_name] = {
                    "name": prop_name,
                    "type": row.get("propType"),
                    "description": row.get("propDesc"),
                    "unit": row.get("propUnit"),
                    "writable": row.get("writable"),
                    "minimum": row.get("minimum"),
                    "maximum": row.get("maximum"),
                }

            cmd_name = row.get("cmdName")
            if cmd_name and cmd_name not in record["commands"]:
                record["commands"][cmd_name] = {
                    "name": cmd_name,
                    "description": row.get("cmdDesc"),
                }

            rel_name = row.get("relName")
            if rel_name and rel_name not in record["relationships"]:
                record["relationships"][rel_name] = {
                    "name": rel_name,
                    "target": self._local_name(row.get("relTarget")),
                    "targetUri": row.get("relTarget"),
                    "type": self._local_name(row.get("relType")),
                    "status": self._local_name(row.get("relStatus")) or "Active",
                }

        # Preserve the caller's ordering — the page order comes from list_interface_uris
        return [records[uri] for uri in uris if uri in records]

    async def get_all_things(
        self,
        page: int = 1,
        page_size: int = 10,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all TwinInterfaces and TwinInstances with pagination.

        Args:
            page: Page number (1-based)
            page_size: Items per page
            tenant_id: Optional tenant filter

        Returns:
            Dict with items list and pagination info
        """
        try:
            graph_filter = self._build_tenant_graph_filter(tenant_id)

            offset = (page - 1) * page_size

            query = f"""
            PREFIX ts: <{self.TS}>
            PREFIX tsd: <{self.TSD}>

            SELECT ?uri ?name ?type ?description ?graph ?originalId ?thingType
            WHERE {{
                GRAPH ?graph {{
                    ?uri ts:name ?name .
                    ?uri a ?type .
                    FILTER(?type IN (ts:TwinInterface, ts:TwinInstance))
                    OPTIONAL {{ ?uri ts:description ?description }}
                    OPTIONAL {{ ?uri ts:originalId ?originalId }}
                    OPTIONAL {{ ?uri ts:thingType ?thingType }}
                }}
                {graph_filter}
            }}
            ORDER BY ?name
            OFFSET {offset}
            LIMIT {page_size}
            """

            results = await self._execute_query(query)
            parsed = self._parse_sparql_results(results)

            items = []
            for row in parsed:
                item = {
                    "id": row.get("uri", ""),
                    "name": row.get("name", ""),
                    "type": "TwinInterface" if "TwinInterface" in row.get("type", "") else "TwinInstance",
                    "description": row.get("description"),
                    "graph": row.get("graph", ""),
                    "originalId": row.get("originalId"),
                    "thingType": row.get("thingType"),
                }
                items.append(item)

            return {
                "items": items,
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "total": len(items)
                }
            }

        except Exception as e:
            logger.error(f"Failed to get all things: {str(e)}")
            raise FusekiException(f"Failed to get all things: {str(e)}")

    async def get_thing_by_id(
        self,
        thing_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single thing (interface or instance) by its URI or name.

        Args:
            thing_id: Thing URI or name
            tenant_id: Optional tenant filter

        Returns:
            Thing details or None
        """
        try:
            graph_filter = self._build_tenant_graph_filter(tenant_id)

            safe_id = thing_id.replace('"', '\\"')

            query = f"""
            PREFIX ts: <{self.TS}>
            PREFIX tsd: <{self.TSD}>

            SELECT ?uri ?name ?type ?description ?graph ?originalId ?thingType
                   ?propName ?propType ?propDesc
            WHERE {{
                GRAPH ?graph {{
                    ?uri a ?type .
                    ?uri ts:name ?name .
                    FILTER(?type IN (ts:TwinInterface, ts:TwinInstance))
                    FILTER(
                        STR(?uri) = "{safe_id}"
                        || STR(?name) = "{safe_id}"
                        || CONTAINS(STR(?graph), "{safe_id}")
                    )
                    OPTIONAL {{ ?uri ts:description ?description }}
                    OPTIONAL {{ ?uri ts:originalId ?originalId }}
                    OPTIONAL {{ ?uri ts:thingType ?thingType }}
                    OPTIONAL {{
                        ?uri ts:hasProperty ?prop .
                        ?prop ts:propertyName ?propName .
                        ?prop ts:propertyType ?propType .
                        OPTIONAL {{ ?prop ts:description ?propDesc }}
                    }}
                }}
                {graph_filter}
            }}
            """

            results = await self._execute_query(query)
            parsed = self._parse_sparql_results(results)

            if not parsed:
                return None

            first = parsed[0]
            thing = {
                "id": first.get("uri", ""),
                "@id": first.get("originalId") or first.get("name", ""),
                "name": first.get("name", ""),
                "title": first.get("name", ""),
                "type": "TwinInterface" if "TwinInterface" in first.get("type", "") else "TwinInstance",
                "description": first.get("description"),
                "graph": first.get("graph", ""),
                "thingType": first.get("thingType"),
                "properties": {}
            }

            seen_props = set()
            for row in parsed:
                prop_name = row.get("propName")
                if prop_name and prop_name not in seen_props:
                    thing["properties"][prop_name] = {
                        "type": row.get("propType", "string"),
                        "description": row.get("propDesc"),
                    }
                    seen_props.add(prop_name)

            return thing

        except Exception as e:
            logger.error(f"Failed to get thing by id: {str(e)}")
            raise FusekiException(f"Failed to get thing by id: {str(e)}")

    async def check_health(self) -> Dict[str, Any]:
        """Check Fuseki connection health"""
        try:
            query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o } LIMIT 1"
            results = await self._execute_query(query)
            parsed = self._parse_sparql_results(results)
            triple_count = parsed[0].get("count", "0") if parsed else "0"

            return {
                "status": "healthy",
                "fuseki_url": self.fuseki_url,
                "dataset": self.dataset,
                "triple_count": triple_count
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "fuseki_url": self.fuseki_url,
                "dataset": self.dataset
            }

    async def search_by_property(
        self,
        property_name: str,
        operator: str = "eq",
        value: float = 0,
        tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Search TwinInterfaces by property schema criteria.

        Finds interfaces that have a matching property and optionally
        filters by the property's min/max range defined in the schema.

        Args:
            property_name: Property name to search for (e.g., 'temperature')
            operator: Comparison operator ('gt', 'gte', 'lt', 'lte', 'eq', 'ne')
            value: Threshold value to compare against property min/max
            tenant_id: Optional tenant filter
            limit: Maximum results

        Returns:
            Dict with results list, count, and metadata
        """
        import time
        start_time = time.time()

        try:
            graph_filter = self._build_tenant_graph_filter(tenant_id)
            safe_prop = property_name.replace('"', '\\"').lower()

            # Build the value filter based on operator
            # We compare against the property's min/max range in the schema
            value_filter = ""
            if operator == "gt":
                value_filter = f"&& (?propMax > {value} || !BOUND(?propMax))"
            elif operator == "gte":
                value_filter = f"&& (?propMax >= {value} || !BOUND(?propMax))"
            elif operator == "lt":
                value_filter = f"&& (?propMin < {value} || !BOUND(?propMin))"
            elif operator == "lte":
                value_filter = f"&& (?propMin <= {value} || !BOUND(?propMin))"
            elif operator == "eq":
                value_filter = f"&& (?propMin <= {value} || !BOUND(?propMin)) && (?propMax >= {value} || !BOUND(?propMax))"

            sparql = f"""
            PREFIX ts: <{self.TS}>
            PREFIX tsd: <{self.TSD}>

            SELECT DISTINCT ?interface ?name ?propName ?propType ?propMin ?propMax ?unit ?description ?graph ?thingType
            WHERE {{
                GRAPH ?graph {{
                    ?interface a ts:TwinInterface .
                    ?interface ts:name ?name .
                    ?interface ts:hasProperty ?prop .
                    ?prop ts:propertyName ?propName .
                    ?prop ts:propertyType ?propType .
                    FILTER(CONTAINS(LCASE(STR(?propName)), "{safe_prop}"))
                    OPTIONAL {{ ?prop ts:minimum ?propMin }}
                    OPTIONAL {{ ?prop ts:maximum ?propMax }}
                    OPTIONAL {{ ?prop ts:unit ?unit }}
                    OPTIONAL {{ ?interface ts:description ?description }}
                    OPTIONAL {{ ?interface ts:thingType ?thingType }}
                }}
                {graph_filter}
                FILTER(true {value_filter})
            }}
            ORDER BY ?name
            LIMIT {limit}
            """

            results = await self._execute_query(sparql)
            parsed = self._parse_sparql_results(results)

            items = []
            for row in parsed:
                items.append({
                    "thingId": row.get("interface", ""),
                    "name": row.get("name", ""),
                    "property": row.get("propName", ""),
                    "propertyType": row.get("propType", ""),
                    "min": row.get("propMin"),
                    "max": row.get("propMax"),
                    "unit": row.get("unit"),
                    "description": row.get("description"),
                    "thingType": row.get("thingType"),
                    "graph": row.get("graph", ""),
                })

            elapsed_ms = round((time.time() - start_time) * 1000, 1)

            return {
                "results": items,
                "count": len(items),
                "schema_matches": len(items),
                "value_matches": len(items),
                "query_time_ms": elapsed_ms,
                "property": property_name,
                "operator": operator,
                "value": value,
            }

        except Exception as e:
            logger.error(f"Failed to search by property: {str(e)}")
            raise FusekiException(f"Failed to search by property: {str(e)}")

    async def get_instance_relationships(
        self,
        instance_name: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all relationships for a TwinInstance

        Args:
            instance_name: Name of the instance
            tenant_id: Optional tenant filter

        Returns:
            List of relationship dictionaries
        """
        try:
            instance_uri = create_instance_uri(instance_name)

            graph_filter = self._build_tenant_graph_filter(tenant_id)

            query = f"""
            PREFIX ts: <{self.TS}>
            PREFIX tsd: <{self.TSD}>

            SELECT ?relName ?targetInstance ?targetInterface ?graph
            WHERE {{
                GRAPH ?graph {{
                    <{instance_uri}> ts:hasInstanceRelationship ?rel .
                    ?rel ts:relationshipName ?relName .
                    ?rel ts:targetInstance ?target .
                    ?target ts:name ?targetInstance .
                    ?target ts:instanceOf ?interface .
                    ?interface ts:name ?targetInterface .
                }}
                {graph_filter}
            }}
            """

            results = await self._execute_query(query)
            return self._parse_sparql_results(results)

        except Exception as e:
            logger.error(f"Failed to get instance relationships: {str(e)}")
            raise FusekiException(f"Failed to get instance relationships: {str(e)}")

    # ========================================================================
    # Private Helper Methods - Tenant Filtering
    # ========================================================================

    async def _insert_inverse_relationships(
        self,
        interface_data: Dict[str, Any],
        tenant_id: str,
    ) -> None:
        """
        For each outgoing relationship with a known inverse type, insert the inverse
        relationship node directly into the TARGET thing's named graph via SPARQL INSERT.

        This ensures each thing's own graph contains its relationships (both forward
        relationships it owns, and inverse relationships that others have toward it).
        Historical data is preserved: when the source is deleted, the inverse node
        in the target's graph is set to Inactive instead of being dropped.
        """
        iface_name = interface_data["metadata"]["name"]
        interface_uri = create_interface_uri(iface_name)
        spec = interface_data.get("spec", {})
        graph_prefix = f"http://twin.io/graphs/{tenant_id}/"

        for rel in spec.get("relationships", []):
            rel_type = rel.get("relationship_type") or rel.get("type", "")
            inverse_type = get_inverse_type(rel_type) if rel_type else None
            if not inverse_type:
                continue

            target_name = rel.get("interface", "")
            if not target_name:
                continue

            target_interface_uri = create_interface_uri(target_name)
            inv_rel_name = f"{rel['name']}-inv"
            inv_rel_uri = create_relationship_uri(target_name, inv_rel_name)

            # Find the target thing's named graph
            find_graph_query = f"""
            PREFIX ts: <{self.TS}>
            SELECT DISTINCT ?g WHERE {{
                GRAPH ?g {{ <{target_interface_uri}> a ts:TwinInterface . }}
                FILTER(STRSTARTS(STR(?g), "{graph_prefix}"))
            }}
            """
            results = await self._execute_query(find_graph_query)
            rows = self._parse_sparql_results(results)
            if not rows:
                logger.warning(
                    f"Cannot insert inverse relationship: target graph not found for '{target_name}'"
                )
                continue

            target_graph_uri = rows[0].get("g", "")
            if not target_graph_uri:
                continue

            insert_query = f"""
            PREFIX ts: <{self.TS}>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            INSERT {{
                GRAPH <{target_graph_uri}> {{
                    <{inv_rel_uri}> a ts:Relationship .
                    <{inv_rel_uri}> ts:relationshipName "{inv_rel_name}" .
                    <{inv_rel_uri}> ts:sourceInterface <{target_interface_uri}> .
                    <{inv_rel_uri}> ts:targetInterface <{interface_uri}> .
                    <{inv_rel_uri}> ts:relationshipType ts:{inverse_type} .
                    <{inv_rel_uri}> ts:relationshipStatus ts:Active .
                    <{target_interface_uri}> ts:hasRelationship <{inv_rel_uri}> .
                }}
            }} WHERE {{}}
            """
            await self._execute_update(insert_query)
            logger.info(
                f"Inserted inverse relationship '{inv_rel_name}' ({inverse_type}) "
                f"into graph: {target_graph_uri}"
            )

    def _build_tenant_graph_filter(self, tenant_id: Optional[str] = None) -> str:
        """
        Build a SPARQL FILTER clause for tenant-based graph filtering.

        Each tenant sees only its own graphs. No cross-tenant bleed.
        """
        effective = tenant_id if tenant_id else "default"
        return f"FILTER(STRSTARTS(STR(?graph), 'http://twin.io/graphs/{effective}/'))"

    # ========================================================================
    # Private Helper Methods - RDF Conversion
    # ========================================================================

    def _add_interface_to_graph(
        self,
        graph: Graph,
        interface_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add TwinInterface to RDF graph"""
        interface_name = interface_data["metadata"]["name"]
        interface_uri = create_interface_uri(interface_name)

        # Interface type
        graph.add((interface_uri, RDF.type, self.TS.TwinInterface))
        graph.add((interface_uri, self.TS.name, Literal(interface_name)))

        # Metadata
        if "labels" in interface_data["metadata"]:
            labels = interface_data["metadata"]["labels"]
            if "generated-by" in labels:
                graph.add((interface_uri, self.TS.generatedBy, Literal(labels["generated-by"])))
            if "generated-at" in labels:
                graph.add((interface_uri, self.TS.generatedAt,
                          Literal(labels["generated-at"], datatype=XSD.dateTime)))
            # NEW: Thing Type
            if "thing-type" in labels:
                graph.add((interface_uri, self.TS.thingType, Literal(labels["thing-type"])))

        if "annotations" in interface_data["metadata"]:
            annotations = interface_data["metadata"]["annotations"]
            if "source" in annotations:
                graph.add((interface_uri, self.TS.sourceFormat, Literal(annotations["source"])))
            if "original-id" in annotations:
                graph.add((interface_uri, self.TS.originalId, Literal(annotations["original-id"])))
            # NEW: Domain Metadata
            if "manufacturer" in annotations:
                graph.add((interface_uri, self.TS.manufacturer, Literal(annotations["manufacturer"])))
            if "model" in annotations:
                graph.add((interface_uri, self.TS.model, Literal(annotations["model"])))
            if "serialNumber" in annotations:
                graph.add((interface_uri, self.TS.serialNumber, Literal(annotations["serialNumber"])))
            if "firmwareVersion" in annotations:
                graph.add((interface_uri, self.TS.firmwareVersion, Literal(annotations["firmwareVersion"])))
            # NEW: DTDL Metadata
            if "dtdl-interface" in annotations:
                graph.add((interface_uri, self.TS.dtdlInterface, Literal(annotations["dtdl-interface"])))
            if "dtdl-interface-name" in annotations:
                graph.add((interface_uri, self.TS.dtdlInterfaceName, Literal(annotations["dtdl-interface-name"])))
            if "dtdl-category" in annotations:
                graph.add((interface_uri, self.TS.dtdlCategory, Literal(annotations["dtdl-category"])))
            # Location (W3C Basic Geo) — makes the twin geographically discoverable
            add_location_triples(graph, interface_uri, annotations)
            # Where an imported twin came from, and the facts it carries
            add_provenance_triples(graph, interface_uri, annotations)
            add_attribute_triples(graph, interface_uri, interface_name, annotations)

        spec = interface_data.get("spec", {})

        # Properties
        for prop in spec.get("properties", []):
            prop_uri = create_property_uri(interface_name, prop["name"])
            graph.add((prop_uri, RDF.type, self.TS.Property))
            graph.add((prop_uri, self.TS.propertyName, Literal(prop["name"])))
            graph.add((prop_uri, self.TS.propertyType, Literal(prop["type"])))

            if "description" in prop and prop["description"]:
                graph.add((prop_uri, self.TS.description, Literal(prop["description"])))
            if "x-writable" in prop:
                graph.add((prop_uri, self.TS.writable, Literal(prop["x-writable"], datatype=XSD.boolean)))
            if "x-minimum" in prop and prop["x-minimum"] is not None:
                graph.add((prop_uri, self.TS.minimum, Literal(prop["x-minimum"])))
            if "x-maximum" in prop and prop["x-maximum"] is not None:
                graph.add((prop_uri, self.TS.maximum, Literal(prop["x-maximum"])))
            if "x-unit" in prop and prop["x-unit"]:
                graph.add((prop_uri, self.TS.unit, Literal(prop["x-unit"])))

            graph.add((interface_uri, self.TS.hasProperty, prop_uri))

        # Relationships
        for rel in spec.get("relationships", []):
            rel_uri = create_relationship_uri(interface_name, rel["name"])
            graph.add((rel_uri, RDF.type, self.TS.Relationship))
            graph.add((rel_uri, self.TS.relationshipName, Literal(rel["name"])))
            # targetInterface: URI referansı
            target_interface_uri = create_interface_uri(rel["interface"])
            graph.add((rel_uri, self.TS.targetInterface, target_interface_uri))
            # sourceInterface: kaynak interface referansı (çift yönlü sorgulama için)
            graph.add((rel_uri, self.TS.sourceInterface, interface_uri))

            # relationshipType (SSN/SOSA type vocabulary)
            rel_type = rel.get("relationship_type") or rel.get("type", "")
            if rel_type and rel_type in INVERSE_TYPE_MAP or rel_type in INVERSE_TYPE_MAP.values():
                graph.add((rel_uri, self.TS.relationshipType, self.TS[rel_type]))
            elif rel_type:
                graph.add((rel_uri, self.TS.relationshipType, self.TS[rel_type]))

            # relationshipStatus: Active by default
            graph.add((rel_uri, self.TS.relationshipStatus, self.TS.Active))

            if "description" in rel and rel["description"]:
                graph.add((rel_uri, self.TS.description, Literal(rel["description"])))

            # Outgoing: kaynak interface → relationship node
            graph.add((interface_uri, self.TS.hasRelationship, rel_uri))

            # Inverse relationship is inserted into the TARGET's named graph
            # via SPARQL INSERT in store_twin_yaml — not here (sync graph only holds source data)

        # Commands
        for cmd in spec.get("commands", []):
            cmd_uri = create_command_uri(interface_name, cmd["name"])
            graph.add((cmd_uri, RDF.type, self.TS.Command))
            graph.add((cmd_uri, self.TS.commandName, Literal(cmd["name"])))

            if "description" in cmd and cmd["description"]:
                graph.add((cmd_uri, self.TS.description, Literal(cmd["description"])))
            if "schema" in cmd:
                graph.add((cmd_uri, self.TS.schema, Literal(json.dumps(cmd["schema"]))))

            graph.add((interface_uri, self.TS.hasCommand, cmd_uri))

    def _add_instance_to_graph(
        self,
        graph: Graph,
        instance_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add TwinInstance to RDF graph"""
        instance_name = instance_data["metadata"]["name"]
        instance_uri = create_instance_uri(instance_name)

        # Instance type
        graph.add((instance_uri, RDF.type, self.TS.TwinInstance))
        graph.add((instance_uri, self.TS.name, Literal(instance_name)))

        # Interface reference
        interface_name = instance_data["spec"]["interface"]
        interface_uri = create_interface_uri(interface_name)
        graph.add((instance_uri, self.TS.instanceOf, interface_uri))

        # Metadata
        if "labels" in instance_data["metadata"]:
            labels = instance_data["metadata"]["labels"]
            if "generated-by" in labels:
                graph.add((instance_uri, self.TS.generatedBy, Literal(labels["generated-by"])))
            if "generated-at" in labels:
                graph.add((instance_uri, self.TS.generatedAt,
                          Literal(labels["generated-at"], datatype=XSD.dateTime)))

        # Location (W3C Basic Geo) — the instance is the deployed twin, so its
        # coordinates are what geographic discovery should match on
        add_location_triples(
            graph, instance_uri, instance_data["metadata"].get("annotations")
        )
        instance_annotations = instance_data["metadata"].get("annotations")
        add_provenance_triples(graph, instance_uri, instance_annotations)
        add_attribute_triples(graph, instance_uri, instance_name, instance_annotations)

        # Instance relationships
        for rel in instance_data["spec"].get("twinInstanceRelationships", []):
            rel_node = BNode()
            graph.add((rel_node, RDF.type, self.TS.InstanceRelationship))
            graph.add((rel_node, self.TS.relationshipName, Literal(rel["name"])))

            target_instance_uri = create_instance_uri(rel["instance"])
            graph.add((rel_node, self.TS.targetInstance, target_instance_uri))

            graph.add((instance_uri, self.TS.hasInstanceRelationship, rel_node))

    # ========================================================================
    # Private Helper Methods - Fuseki Communication
    # ========================================================================

    async def _store_graph(self, graph: Graph):
        """Store RDF graph in Fuseki default graph (deprecated - use _store_named_graph)"""
        try:
            # Serialize to Turtle
            turtle_data = graph.serialize(format="turtle")

            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(self.username, self.password)
                headers = {"Content-Type": "text/turtle"}

                async with session.post(
                    self.data_endpoint,
                    data=turtle_data,
                    headers=headers,
                    auth=auth
                ) as response:
                    if response.status not in [200, 201, 204]:
                        error_text = await response.text()
                        raise FusekiException(
                            f"Failed to store graph: {response.status} - {error_text}"
                        )

        except Exception as e:
            logger.error(f"Failed to store graph in Fuseki: {str(e)}")
            raise

    async def _store_named_graph(self, graph: Graph, graph_uri: str):
        """
        Store RDF graph in Fuseki as a Named Graph

        Args:
            graph: RDF graph to store
            graph_uri: URI of the named graph (e.g., http://twin.io/graphs/tenant1/thing1)
        """
        try:
            # Serialize to Turtle
            turtle_data = graph.serialize(format="turtle")

            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(self.username, self.password)
                headers = {"Content-Type": "text/turtle"}

                # Use PUT to create/replace named graph
                # Fuseki endpoint: /data?graph=<uri>
                named_graph_endpoint = f"{self.data_endpoint}?graph={graph_uri}"

                async with session.put(
                    named_graph_endpoint,
                    data=turtle_data,
                    headers=headers,
                    auth=auth
                ) as response:
                    if response.status not in [200, 201, 204]:
                        error_text = await response.text()
                        raise FusekiException(
                            f"Failed to store named graph: {response.status} - {error_text}"
                        )

                    logger.info(f"Successfully stored named graph: {graph_uri}")

        except Exception as e:
            logger.error(f"Failed to store named graph in Fuseki: {str(e)}")
            raise

    async def _execute_query(self, query: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute a SPARQL read query.

        Args:
            query: SPARQL query text
            timeout: Wall clock budget in seconds; falls back to
                SPARQL_TIMEOUT_SECONDS so a runaway query cannot hold a
                connection open indefinitely.
        """
        budget = aiohttp.ClientTimeout(total=timeout or settings.SPARQL_TIMEOUT_SECONDS)
        try:
            async with aiohttp.ClientSession(timeout=budget) as session:
                auth = aiohttp.BasicAuth(self.username, self.password)
                headers = {"Accept": "application/sparql-results+json"}

                async with session.post(
                    self.query_endpoint,
                    data={"query": query},
                    headers=headers,
                    auth=auth
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise FusekiException(
                            f"SPARQL query failed: {response.status} - {error_text}"
                        )

                    return await response.json()

        except Exception as e:
            logger.error(f"Failed to execute SPARQL query: {str(e)}")
            raise

    async def _execute_update(self, update: str):
        """Execute SPARQL UPDATE query"""
        try:
            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(self.username, self.password)
                headers = {"Content-Type": "application/sparql-update"}

                async with session.post(
                    self.update_endpoint,
                    data=update,
                    headers=headers,
                    auth=auth
                ) as response:
                    if response.status not in [200, 204]:
                        error_text = await response.text()
                        raise FusekiException(
                            f"SPARQL update failed: {response.status} - {error_text}"
                        )

        except Exception as e:
            logger.error(f"Failed to execute SPARQL update: {str(e)}")
            raise

    # ========================================================================
    # Private Helper Methods - Result Parsing
    # ========================================================================

    def _parse_sparql_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse SPARQL JSON results into list of dictionaries"""
        parsed = []
        for binding in results.get("results", {}).get("bindings", []):
            row = {}
            for var, value in binding.items():
                row[var] = value.get("value")
            parsed.append(row)
        return parsed

    def _parse_interface_details(self, results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse interface details from SPARQL results"""
        bindings = results.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        # First binding has basic info
        first = bindings[0]
        interface = {
            "name": first.get("name", {}).get("value"),
            "description": first.get("description", {}).get("value"),
            "generatedAt": first.get("generatedAt", {}).get("value"),
            "generatedBy": first.get("generatedBy", {}).get("value"),
            "properties": [],
            "relationships": [],
            "commands": []
        }

        # Collect properties, relationships, commands
        seen_props = set()
        seen_rels = set()
        seen_cmds = set()

        for binding in bindings:
            # Properties
            if "propName" in binding:
                prop_name = binding["propName"]["value"]
                if prop_name not in seen_props:
                    interface["properties"].append({
                        "name": prop_name,
                        "type": binding.get("propType", {}).get("value"),
                        "description": binding.get("propDesc", {}).get("value"),
                        "writable": binding.get("writable", {}).get("value") == "true"
                    })
                    seen_props.add(prop_name)

            # Relationships
            if "relName" in binding:
                rel_name = binding["relName"]["value"]
                if rel_name not in seen_rels:
                    rel_type_uri = binding.get("relType", {}).get("value", "")
                    rel_type_short = rel_type_uri.split("#")[-1] if rel_type_uri else ""
                    rel_status_uri = binding.get("relStatus", {}).get("value", "")
                    rel_status_short = rel_status_uri.split("#")[-1] if rel_status_uri else "Active"
                    # targetInterface URI'den name çıkar
                    rel_target_uri = binding.get("relTarget", {}).get("value", "")
                    rel_target_name = rel_target_uri.split("/")[-1] if rel_target_uri else ""
                    interface["relationships"].append({
                        "name": rel_name,
                        "targetInterface": rel_target_name or rel_target_uri,
                        "description": binding.get("relDesc", {}).get("value"),
                        "relationshipType": rel_type_short,
                        "status": rel_status_short,
                    })
                    seen_rels.add(rel_name)

            # Commands
            if "cmdName" in binding:
                cmd_name = binding["cmdName"]["value"]
                if cmd_name not in seen_cmds:
                    interface["commands"].append({
                        "name": cmd_name,
                        "description": binding.get("cmdDesc", {}).get("value")
                    })
                    seen_cmds.add(cmd_name)

        return interface


# ============================================================================
# Convenience Functions
# ============================================================================

def create_twin_rdf_service() -> TwinRDFService:
    """Factory function to create TwinRDFService with default settings"""
    return TwinRDFService()


__all__ = [
    "TwinRDFService",
    "create_twin_rdf_service",
]
