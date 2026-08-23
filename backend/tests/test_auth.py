"""Authentication behavior tests."""

from app.models.user import User
from fastapi.testclient import TestClient


def test_login_returns_user_and_bearer_token(
    client: TestClient,
    administrator: User,
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ADMIN@ARVA.LOCAL", "password": "ValidPassword!1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 1800
    assert payload["user"]["role"] == "administrator"
    assert payload["user"]["organization"]["slug"] == "test-org"
    assert "password_hash" not in payload["user"]
    assert response.cookies["arva_access_token"] == payload["access_token"]


def test_cookie_session_authenticates_and_logout_clears_it(
    client: TestClient,
    administrator: User,
) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": administrator.email, "password": "ValidPassword!1"},
    )

    assert login.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200

    logout = client.post("/api/v1/auth/logout")

    assert logout.status_code == 204
    assert "arva_access_token" not in client.cookies
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_rejects_invalid_credentials(
    client: TestClient,
    administrator: User,
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": administrator.email, "password": "WrongPassword!1"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.json()["error"]["request_id"].startswith("REQ-")


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
