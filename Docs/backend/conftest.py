import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / 'Backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from repository.ListingRepository import ListingRepository
from service.ListingService import ListingService
from flask import Flask


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / 'test_property.db')


@pytest.fixture
def schema_path():
    return str(BACKEND_DIR / 'database.sql')


@pytest.fixture
def repository(temp_db_path, schema_path):
    repo = ListingRepository(temp_db_path)
    repo.create_tables_from_schema(schema_path)
    return repo


@pytest.fixture
def service(repository):
    return ListingService(repository)


@pytest.fixture
def sample_transport_points(repository):
    repository.insert_transport_point('Metro A', 'Metro', 25.2048, 55.2708, 'M1')
    repository.insert_transport_point('Bus A', 'Bus', 25.2058, 55.2708, 'B1')
    repository.insert_transport_point('Metro B', 'Metro', 25.2148, 55.2808, 'M2')
    repository.insert_transport_point('Bus B', 'Bus', 25.2248, 55.2908, 'B2')
    return repository.get_all_transport_points()


@pytest.fixture
def valid_listing_payload():
    return {
        'title': '2 Bedroom Apartment',
        'price': 1200000,
        'latitude': 25.2049,
        'longitude': 55.2709,
        'source_url': 'https://example.com/listing-1',
        'bedrooms': 2,
        'bathrooms': 2,
        'area_sqft': 1200,
        'source_site': 'PropertyFinder',
        'realtor_name': 'Test Agent',
        'realtor_contact': '0500000000',
    }


@pytest.fixture
def app_with_test_db(temp_db_path, schema_path):
    from routes.ListingRoutes import listing_bp
    from routes import ListingRoutes

    test_repo = ListingRepository(temp_db_path)
    test_repo.create_tables_from_schema(schema_path)
    test_service = ListingService(test_repo)

    ListingRoutes.repository = test_repo
    ListingRoutes.service = test_service

    app = Flask(__name__)
    app.config.update(TESTING=True)
    app.register_blueprint(listing_bp)
    yield app, test_repo, test_service


@pytest.fixture
def client(app_with_test_db):
    app, _, _ = app_with_test_db
    return app.test_client()
