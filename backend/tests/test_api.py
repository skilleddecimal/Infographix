"""Tests for API endpoints - basic unauthenticated tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta

from backend.db.base import Base, get_db
from backend.db.models import User, Session as UserSession, Template
from backend.api.routes.auth import hash_password, hash_token


@pytest.fixture(scope="function")
def test_db():
    """Create test database with thread-safe SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
        name="Test User",
        credits_remaining=10,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_db, test_user):
    """Create an auth token for test user."""
    token = "test_access_token"
    session = UserSession(
        user_id=test_user.id,
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    test_db.add(session)
    test_db.commit()
    return token


@pytest.fixture
def client(test_db):
    """Create test client with mocked database."""
    from backend.api.main import create_app

    app = create_app()

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_list_templates_requires_auth(client: TestClient) -> None:
    """Test templates endpoint requires authentication."""
    response = client.get("/api/v1/templates")
    assert response.status_code == 401


def test_list_templates(client: TestClient, test_db, test_user, auth_token) -> None:
    """Test templates endpoint returns list of templates."""
    # Create a public template
    template = Template(
        user_id=test_user.id,
        name="Test Template",
        dsl_template={"shapes": []},
        is_public=True,
    )
    test_db.add(template)
    test_db.commit()

    response = client.get(
        "/api/v1/templates",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert isinstance(data["templates"], list)


def test_generate_endpoint_requires_auth(client: TestClient) -> None:
    """Test generate endpoint requires authentication."""
    response = client.post(
        "/api/v1/generate",
        json={"prompt": "Create a 5-stage sales funnel"},
    )
    assert response.status_code == 401


def test_generate_endpoint_exists(client: TestClient, auth_token) -> None:
    """Test generate endpoint accepts requests."""
    response = client.post(
        "/api/v1/generate",
        json={"prompt": "Create a 5-stage sales funnel"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "status" in data


def test_generate_requires_prompt(client: TestClient, auth_token) -> None:
    """Test generate endpoint requires prompt field."""
    response = client.post(
        "/api/v1/generate",
        json={},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422  # Validation error
