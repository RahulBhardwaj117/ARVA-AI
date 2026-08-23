"""Role-based authorization tests."""

from app.models.user import User
from fastapi.testclient import TestClient


def login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "ValidPassword!1"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_administrator_can_access_operator_boundary(
    client: TestClient,
    administrator: User,
) -> None:
    token = login(client, administrator.email)

    response = client.get(
        "/api/v1/operator-check",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_viewer_cannot_access_operator_boundary(
    client: TestClient,
    viewer: User,
) -> None:
    token = login(client, viewer.email)

    response = client.get(
        "/api/v1/operator-check",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
