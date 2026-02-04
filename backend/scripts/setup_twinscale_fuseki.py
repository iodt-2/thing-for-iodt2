"""
Setup TwinScale Fuseki Database

This script creates the twinscale-db dataset in Fuseki and loads the TwinScale ontology.

Usage:
    python scripts/setup_twinscale_fuseki.py
"""

import requests
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.twinscale_ontology import get_twinscale_ontology

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def create_dataset(dataset_name: str = "twinscale-db") -> bool:
    """
    Create a new TDB2 dataset in Fuseki

    Args:
        dataset_name: Name of the dataset to create

    Returns:
        bool: True if successful or already exists
    """
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


def load_ontology(dataset_name: str = "twinscale-db") -> bool:
    """
    Load TwinScale ontology into the dataset

    Args:
        dataset_name: Name of the dataset

    Returns:
        bool: True if successful
    """
    try:
        logger.info("Loading TwinScale ontology...")

        fuseki_url = settings.FUSEKI_URL
        auth = (settings.FUSEKI_USERNAME, settings.FUSEKI_PASSWORD)

        # Get ontology graph
        ontology = get_twinscale_ontology()

        # Serialize to Turtle
        turtle_data = ontology.serialize(format="turtle")

        # Upload to Fuseki
        data_url = f"{fuseki_url}/{dataset_name}/data"
        headers = {"Content-Type": "text/turtle"}

        response = requests.post(
            data_url,
            data=turtle_data,
            headers=headers,
            auth=auth
        )

        if response.status_code in [200, 201, 204]:
            logger.info(f"✓ TwinScale ontology loaded successfully ({len(ontology)} triples)")
            return True
        else:
            logger.error(f"✗ Failed to load ontology: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"✗ Error loading ontology: {str(e)}")
        return False


def verify_setup(dataset_name: str = "twinscale-db") -> bool:
    """
    Verify the setup by running a test query

    Args:
        dataset_name: Name of the dataset

    Returns:
        bool: True if verification successful
    """
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
    logger.info("TwinScale Fuseki Database Setup")
    logger.info("=" * 60)
    logger.info(f"Fuseki URL: {settings.FUSEKI_URL}")
    logger.info(f"Dataset: twinscale-db")
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
    logger.info("✓ TwinScale Fuseki setup completed successfully!")
    logger.info("=" * 60)
    logger.info(f"Query endpoint: {settings.FUSEKI_URL}/twinscale-db/query")
    logger.info(f"Update endpoint: {settings.FUSEKI_URL}/twinscale-db/update")
    logger.info(f"Data endpoint: {settings.FUSEKI_URL}/twinscale-db/data")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
