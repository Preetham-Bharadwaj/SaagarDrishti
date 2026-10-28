"""Pytest shared fixtures and test configuration."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Provide a TestClient instance for testing API endpoints."""
    return TestClient(app)
