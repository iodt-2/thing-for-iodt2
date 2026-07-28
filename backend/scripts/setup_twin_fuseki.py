"""
Setup Twin Fuseki Database

This script creates the Fuseki dataset and loads the Twin ontology.
Dataset name is read from FUSEKI_DATASET setting.

Usage:
    python scripts/setup_twin_fuseki.py
"""

import requests
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.twin_ontology import get_twin_ontology, ONTOLOGY_URI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def create_dataset(dataset_name: str = None) -> bool:
    """
    Create a new TDB2 dataset in Fuseki

    Args:
        dataset_name: Name of the dataset to create

    Returns:
        bool: True if successful or already exists
    """
    dataset_name = dataset_name or settings.FUSEKI_DATASET
    try:
        fuseki_url = settings.FUSEKI_URL
        auth = (settings.FUSEKI_USERNAME, settings.FUSEKI_PASSWORD)

        # Check if dataset already exists
        check_url = f"{fuseki_url}/$/datasets"
        response = requests.get(check_url, auth=auth)

        if response.status_code == 200:
            datasets = response.json()
            existing_datasets = [ds.get("ds.name", "").strip("/") for ds in datasets.get("datasets", [])]

            if dataset_name in existing_datasets:
                logger.info(f"Dataset '{dataset_name}' already exists")
                return True

        # Create new dataset
        logger.info(f"Creating dataset '{dataset_name}'...")
        create_url = f"{fuseki_url}/$/datasets"

        data = {
            "dbName": dataset_name,
            "dbType": "tdb2"
        }

        response = requests.post(
            create_url,
            data=data,
            auth=auth
        )

        if response.status_code in [200, 201]:
            logger.info(f"✓ Dataset '{dataset_name}' created successfully")
            return True
        else:
            logger.error(f"✗ Failed to create dataset: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"✗ Error creating dataset: {str(e)}")
        return False


def load_ontology(dataset_name: str = None) -> bool:
    """
    Load Twin ontology into the dataset

    Args:
        dataset_name: Name of the dataset

    Returns:
        bool: True if successful
    """
    dataset_name = dataset_name or settings.FUSEKI_DATASET
    try:
        logger.info("Loading Twin ontology...")

        fuseki_url = settings.FUSEKI_URL
        auth = (settings.FUSEKI_USERNAME, settings.FUSEKI_PASSWORD)

        # Get ontology graph
        ontology = get_twin_ontology()

        # Serialize to Turtle
        turtle_data = ontology.serialize(format="turtle")

        # Upload to Fuseki — PUT into the ontology's own named graph so repeated
        # runs replace it instead of piling up duplicate triples
        data_url = f"{fuseki_url}/{dataset_name}/data"
        headers = {"Content-Type": "text/turtle"}

        response = requests.put(
            data_url,
            params={"graph": str(ONTOLOGY_URI)},
            data=turtle_data.encode("utf-8"),
            headers=headers,
            auth=auth
        )

        if response.status_code in [200, 201, 204]:
            logger.info(f"✓ Twin ontology loaded successfully ({len(ontology)} triples)")
            return True
        else:
            logger.error(f"✗ Failed to load ontology: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"✗ Error loading ontology: {str(e)}")
        return False


def verify_setup(dataset_name: str = None) -> bool:
    """
    Verify the setup by running a test query

    Args:
        dataset_name: Name of the dataset

    Returns:
        bool: True if verification successful
    """
    dataset_name = dataset_name or settings.FUSEKI_DATASET
    try:
        logger.info("Verifying setup...")

        fuseki_url = settings.FUSEKI_URL
        auth = (settings.FUSEKI_USERNAME, settings.FUSEKI_PASSWORD)

        # Test query: Count triples
        query = """
        SELECT (COUNT(*) as ?count)
        WHERE {
            ?s ?p ?o
        }
        """

        query_url = f"{fuseki_url}/{dataset_name}/query"
        headers = {"Accept": "application/sparql-results+json"}

        response = requests.post(
            query_url,
            data={"query": query},
            headers=headers,
            auth=auth
        )

        if response.status_code == 200:
            results = response.json()
            count = results["results"]["bindings"][0]["count"]["value"]
            logger.info(f"✓ Setup verified: {count} triples in database")
            return True
        else:
            logger.error(f"✗ Verification failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"✗ Error verifying setup: {str(e)}")
        return False


def main():
    """Main setup function"""
    logger.info("=" * 60)
    logger.info("Twin Fuseki Database Setup")
    logger.info("=" * 60)
    logger.info(f"Fuseki URL: {settings.FUSEKI_URL}")
    logger.info(f"Dataset: {settings.FUSEKI_DATASET}")
    logger.info("=" * 60)

    # Step 1: Create dataset
    if not create_dataset():
        logger.error("Setup failed at dataset creation")
        sys.exit(1)

    # Step 2: Load ontology
    if not load_ontology():
        logger.error("Setup failed at ontology loading")
        sys.exit(1)

    # Step 3: Verify
    if not verify_setup():
        logger.error("Setup verification failed")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("✓ Twin Fuseki setup completed successfully!")
    logger.info("=" * 60)
    logger.info(f"Query endpoint: {settings.FUSEKI_URL}/{settings.FUSEKI_DATASET}/query")
    logger.info(f"Update endpoint: {settings.FUSEKI_URL}/{settings.FUSEKI_DATASET}/update")
    logger.info(f"Data endpoint: {settings.FUSEKI_URL}/{settings.FUSEKI_DATASET}/data")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
