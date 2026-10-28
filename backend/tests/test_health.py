"""Tests for API root and health check endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Ensure root endpoint responds with basic service information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SaagarDrishti"
    assert "version" in data
    assert "docs_url" in data


def test_health_check_endpoint(client: TestClient):
    """Ensure health endpoint returns operational status and metadata."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "SaagarDrishti"
    assert "version" in data
    assert "timestamp" in data
