"""
Pytest fixtures for Emoji Team Generator test suite.
Uses temporary SQLite database files for isolated, reproducible tests.
"""

import os
import tempfile
import pytest
from app import create_app
from config import TestConfig
from database import init_db, connect_db
from auth import create_admin_account


@pytest.fixture
def app():
    """Creates a fresh test application instance with an isolated database."""
    # Create a temporary file for the SQLite database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    class CustomTestConfig(TestConfig):
        DATABASE_PATH = db_path
        TESTING = True
        SECRET_KEY = "test-secret-suite-key"
        ADMIN_RATE_LIMIT_MAX_ATTEMPTS = 50  # Prevent test failures due to rate limiting

    app_instance = create_app(CustomTestConfig)

    yield app_instance

    # Cleanup temporary database
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass


@pytest.fixture
def client(app):
    """Provides a Flask test client for making simulated HTTP requests."""
    return app.test_client()


@pytest.fixture
def admin_client(app, client):
    """Provides an authenticated admin test client with valid session and CSRF token."""
    with app.app_context():
        conn = connect_db(app.config["DATABASE_PATH"])
        create_admin_account("testadmin", "TestPassword123!", conn=conn)
        conn.close()

    # Login via API
    resp = client.post("/api/admin/login", json={
        "username": "testadmin",
        "password": "TestPassword123!"
    })
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    csrf_token = data["csrf_token"]

    # Attach CSRF token helper to client
    client.csrf_token = csrf_token
    return client
