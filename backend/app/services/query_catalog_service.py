"""
Query Catalog Service

Serves the saved SPARQL searches from a data file instead of a React component,
so adding one needs no frontend rebuild.

Entries are parsed as SPARQL at load time. A broken query is dropped with a
warning rather than handed to the UI — the catalog is meant to be the set of
searches that are known to work.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from rdflib.plugins.sparql import prepareQuery

logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).resolve().parents[1] / "queries" / "discovery_queries.yaml"

REQUIRED_FIELDS = ("id", "name", "query")

# Placeholder a catalog query can carry to opt into tenant scoping. Substituted
# with a graph FILTER when the query is executed, and removed when the text is
# shown to a user for editing.
#
# Substitution rather than SPARQL rewriting is deliberate: rewriting arbitrary
# queries to inject a filter is fragile, and a filter silently added in the
# wrong place is worse than none. A query without the placeholder is reported
# as tenant_scoped=false so the caller knows it spans tenants.
TENANT_PLACEHOLDER = "#{TENANT}"


def tenant_filter(tenant_id: str) -> str:
    """Graph FILTER restricting results to one tenant's named graphs."""
    return f"FILTER(STRSTARTS(STR(?g), 'http://twin.io/graphs/{tenant_id}/'))"


class QueryCatalogService:
    """Loads and serves the saved query catalog."""

    def __init__(self, catalog_path: Optional[Path] = None):
        self.catalog_path = catalog_path or CATALOG_PATH
        self._entries: Optional[List[Dict[str, Any]]] = None

    def _load(self) -> List[Dict[str, Any]]:
        if self._entries is not None:
            return self._entries

        try:
            raw = yaml.safe_load(self.catalog_path.read_text(encoding="utf-8")) or {}
        except FileNotFoundError:
            logger.warning(f"Query catalog not found at {self.catalog_path}")
            self._entries = []
            return self._entries
        except yaml.YAMLError as exc:
            logger.error(f"Query catalog is not valid YAML: {exc}")
            self._entries = []
            return self._entries

        entries: List[Dict[str, Any]] = []
        seen_ids = set()

        for index, entry in enumerate(raw.get("queries", [])):
            missing = [field for field in REQUIRED_FIELDS if not entry.get(field)]
            if missing:
                logger.warning(f"Catalog entry {index} is missing {missing}; skipped")
                continue

            if entry["id"] in seen_ids:
                logger.warning(f"Duplicate catalog id '{entry['id']}'; skipped")
                continue

            try:
                prepareQuery(entry["query"])
            except Exception as exc:
                logger.warning(
                    f"Catalog entry '{entry['id']}' is not valid SPARQL and was "
                    f"dropped: {exc}"
                )
                continue

            seen_ids.add(entry["id"])
            scoped = TENANT_PLACEHOLDER in entry["query"]
            if not scoped:
                logger.debug(
                    f"Catalog entry '{entry['id']}' has no {TENANT_PLACEHOLDER} "
                    f"placeholder and will span every tenant"
                )

            entries.append({
                "id": entry["id"],
                "category": entry.get("category", "other"),
                "name": entry["name"],
                "description": entry.get("description", ""),
                # Text shown to the user, with the placeholder removed
                "query": entry["query"].replace(TENANT_PLACEHOLDER, "").rstrip(),
                "tenant_scoped": scoped,
                "_raw_query": entry["query"],
            })

        logger.info(f"Query catalog loaded: {len(entries)} queries")
        self._entries = entries
        return entries

    @staticmethod
    def _public(entry: Dict[str, Any]) -> Dict[str, Any]:
        """Entry without the internal raw query."""
        return {key: value for key, value in entry.items() if not key.startswith("_")}

    def list_queries(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        entries = self._load()
        if category and category != "all":
            entries = [entry for entry in entries if entry["category"] == category]
        return [self._public(entry) for entry in entries]

    def get_query(self, query_id: str) -> Optional[Dict[str, Any]]:
        entry = next((e for e in self._load() if e["id"] == query_id), None)
        return self._public(entry) if entry else None

    def render_query(self, query_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        A catalog query ready to execute against one tenant.

        Returns the entry with an extra "executable" field. When the query
        carries no tenant placeholder the text is unchanged and tenant_scoped
        stays false — the caller is expected to surface that.
        """
        entry = next((e for e in self._load() if e["id"] == query_id), None)
        if entry is None:
            return None

        result = self._public(entry)
        result["executable"] = entry["_raw_query"].replace(
            TENANT_PLACEHOLDER, tenant_filter(tenant_id)
        )
        return result

    def categories(self) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for entry in self._load():
            counts[entry["category"]] = counts.get(entry["category"], 0) + 1
        return [
            {"id": name, "count": count}
            for name, count in sorted(counts.items())
        ]

    def reload(self) -> None:
        """Drop the cache so the next read picks up file edits."""
        self._entries = None


_catalog: Optional[QueryCatalogService] = None


def get_query_catalog() -> QueryCatalogService:
    """Shared catalog instance."""
    global _catalog
    if _catalog is None:
        _catalog = QueryCatalogService()
    return _catalog
