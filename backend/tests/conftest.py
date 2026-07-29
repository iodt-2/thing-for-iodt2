"""
Shared pytest setup.

Puts the backend package on sys.path so tests can `from app...` regardless of
where pytest is invoked from.
"""

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session")
def ontology():
    """A private ontology graph — safe for tests that add triples to it."""
    from app.core.twin_ontology import get_twin_ontology

    return get_twin_ontology()


class LocalTwinStore:
    """
    In-memory stand-in for Fuseki.

    Runs the service's real SPARQL text against an rdflib Dataset laid out with
    the same named graphs, so query bugs surface without a running triple
    store. Mocking the service methods instead would test nothing about the
    queries, which is where the interesting mistakes live.
    """

    def __init__(self):
        import json

        from rdflib import Dataset
        from app.services.twin_generator_service import TwinGeneratorService
        from app.services.twin_rdf_service import TwinRDFService

        self._json = json
        self.dataset = Dataset()
        self.generator = TwinGeneratorService()
        self.service = TwinRDFService()
        self.service._execute_query = self.execute

    def graph_uri(self, tenant: str, thing_id: str) -> str:
        return f"http://twin.io/graphs/{tenant}/{thing_id}"

    def add_thing(self, thing_description, tenant: str = "default") -> str:
        """Store a thing exactly the way the create endpoint would."""
        import yaml
        from rdflib import URIRef

        thing_description.setdefault("properties", {})
        thing_description.setdefault("actions", {})
        thing_description.setdefault("links", [])

        thing_id = thing_description["@id"]
        interface_yaml = self.generator.generate_twin_interface_yaml(
            thing_description,
            tenant_id=tenant,
            thing_type=thing_description.get("thing_type", "atomic"),
            domain_metadata=thing_description.get("domain_metadata"),
        )
        instance_yaml = self.generator.generate_twin_instance_yaml(
            thing_description, tenant_id=tenant
        )

        named = self.dataset.graph(URIRef(self.graph_uri(tenant, thing_id)))
        self.service._add_interface_to_graph(
            named, yaml.safe_load(interface_yaml), {"tenant_id": tenant}
        )
        self.service._add_instance_to_graph(
            named, yaml.safe_load(instance_yaml), {"tenant_id": tenant}
        )
        return self.generator._normalize_name(thing_id, tenant)

    async def execute(self, query, timeout=None):
        """Answer a SPARQL query in the shape Fuseki would."""
        return self._json.loads(self.dataset.query(query).serialize(format="json"))


@pytest.fixture
def twin_store(monkeypatch):
    """A local store wired into every TwinRDFService instance the code creates."""
    from app.services.twin_rdf_service import TwinRDFService

    store = LocalTwinStore()
    monkeypatch.setattr(
        TwinRDFService,
        "_execute_query",
        lambda self, query, timeout=None: store.execute(query),
    )
    # The probe cache is class level; keep tests from leaking into each other
    monkeypatch.setattr(TwinRDFService, "_text_index_available", {})
    return store


@pytest.fixture
def discovery_client(twin_store):
    """TestClient over the discovery routers, backed by the local store."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.v2.discovery import router, things_router, well_known_router

    app = FastAPI()
    app.include_router(well_known_router)
    app.include_router(router, prefix="/api/v2")
    app.include_router(things_router, prefix="/api/v2")
    return TestClient(app)
