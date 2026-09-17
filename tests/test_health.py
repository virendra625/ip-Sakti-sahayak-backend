"""Tests for health check endpoint."""

from fastapi import status


def test_health_check(client):
    """Test that GET /api/v1/health returns 200 and healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    assert "components" in data
    assert data["components"]["api"] == "healthy"
    assert "X-Request-ID" in response.headers
