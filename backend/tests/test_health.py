"""Health endpoint tests."""

from fastapi.testclient import TestClient


def test_health_returns_liveness(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "arva-api",
        "version": "0.1.0",
        "checks": None,
    }
    assert response.headers["x-request-id"].startswith("REQ-")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"].startswith("default-src 'none'")
