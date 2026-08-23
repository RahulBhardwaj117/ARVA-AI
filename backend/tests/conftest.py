"""Shared API test fixtures."""

import os

os.environ["ARVA_DATABASE_URL"] = "sqlite://"
os.environ["ARVA_REDIS_URL"] = "redis://localhost:6399/15"
os.environ["ARVA_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-jwt"

import pytest
from app.auth.passwords import hash_password
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.main import app
from app.models.organization import Organization
from app.models.user import User, UserRole
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def reset_database() -> None:
    """Create a clean in-memory database around each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session() -> Session:
    """Return a database session for fixture setup."""
    with SessionLocal() as database_session:
        yield database_session


@pytest.fixture
def organization(session: Session) -> Organization:
    """Create a test tenant."""
    organization = Organization(name="Test Org", slug="test-org")
    session.add(organization)
    session.commit()
    session.refresh(organization)
    return organization


@pytest.fixture
def administrator(session: Session, organization: Organization) -> User:
    """Create an administrator with a known password."""
    user = User(
        organization_id=organization.id,
        name="Admin User",
        email="admin@arva.local",
        password_hash=hash_password("ValidPassword!1"),
        role=UserRole.ADMINISTRATOR,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def viewer(session: Session, organization: Organization) -> User:
    """Create a read-only viewer."""
    user = User(
        organization_id=organization.id,
        name="Viewer User",
        email="viewer@example.com",
        password_hash=hash_password("ValidPassword!1"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def client() -> TestClient:
    """Return a synchronous FastAPI test client."""
    return TestClient(app)


def login(client: TestClient, email: str) -> str:
    """Authenticate a fixture user and return its access token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "ValidPassword!1"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]
