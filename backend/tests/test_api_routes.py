"""Tests for API routes."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base, get_db
from backend.db.models import (
    User,
    Session as UserSession,
    Generation,
    GenerationStatus,
    Template,
    PlanType,
)
from backend.api.routes.auth import hash_password, hash_token


# Test fixtures
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
def test_session(test_db, test_user):
    """Create a test session."""
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


class TestHealthRoutes:
    """Tests for health check routes."""

    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAuthRoutes:
    """Tests for authentication routes."""

    def test_register_success(self, client, test_db):
        """Test successful registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "SecurePass123!",  # Strong password with uppercase, number, special char
                "name": "New User",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "SecurePass123!",  # Strong password
            },
        )
        assert response.status_code == 409

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401


class TestGenerateRoutes:
    """Tests for generation routes."""

    def test_create_generation_unauthorized(self, client):
        """Test generation without auth."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "Create a funnel"},
        )
        assert response.status_code == 401

    def test_create_generation_success(self, client, test_session):
        """Test successful generation creation."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "Create a sales funnel with 4 stages"},
            headers={"Authorization": f"Bearer {test_session}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"

    def test_get_generation(self, client, test_db, test_user, test_session):
        """Test getting a generation."""
        # Create a generation
        generation = Generation(
            user_id=test_user.id,
            prompt="Test prompt",
            status=GenerationStatus.COMPLETED,
            archetype="funnel",
            dsl={"shapes": []},
        )
        test_db.add(generation)
        test_db.commit()

        response = client.get(
            f"/api/v1/generate/{generation.id}",
            headers={"Authorization": f"Bearer {test_session}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == generation.id
        assert data["archetype"] == "funnel"

    def test_get_generation_not_found(self, client, test_session):
        """Test getting nonexistent generation."""
        response = client.get(
            "/api/v1/generate/nonexistent-id",
            headers={"Authorization": f"Bearer {test_session}"},
        )
        assert response.status_code == 404

    def test_list_generations(self, client, test_db, test_user, test_session):
        """Test listing generations."""
        # Create some generations
        for i in range(3):
            gen = Generation(
                user_id=test_user.id,
                prompt=f"Test {i}",
                status=GenerationStatus.COMPLETED,
            )
            test_db.add(gen)
        test_db.commit()

        response = client.get(
            "/api/v1/generate",
            headers={"Authorization": f"Bearer {test_session}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestTemplateRoutes:
    """Tests for template routes."""

    def test_list_templates(self, client, test_db, test_user, test_session):
        """Test listing templates."""
        # Create templates
        template = Template(
            user_id=test_user.id,
            name="My Template",
            dsl_template={"shapes": []},
        )
        test_db.add(template)
        test_db.commit()

        response = client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {test_session}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["templates"]) == 1

    def test_get_template(self, client, test_db, test_user, test_session):
        """Test getting a template."""
        template = Template(
            user_id=test_user.id,
            name="Test Template",
            archetype="funnel",
            dsl_template={"shapes": []},
        )
        test_db.add(template)
        test_db.commit()

        response = client.get(
            f"/api/v1/templates/{template.id}",
            headers={"Authorization": f"Bearer {test_session}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Template"

    def test_create_template_requires_pro(self, client, test_session):
        """Test that creating templates requires Pro plan."""
        response = client.post(
            "/api/v1/templates",
            json={
                "name": "New Template",
                "dsl_template": {"shapes": []},
            },
            headers={"Authorization": f"Bearer {test_session}"},
        )
        # Should fail because user is on Free plan
        assert response.status_code == 403


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_headers(self, client, test_session):
        """Test that rate limit headers are present."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "Test"},
            headers={"Authorization": f"Bearer {test_session}"},
        )

        # Rate limit headers should be present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


class TestSecurityHeaders:
    """Tests for security headers."""

    def test_security_headers_present(self, client):
        """Test that security headers are present."""
        response = client.get("/health")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers


class TestCreditSystem:
    """Tests for credit system."""

    def test_credits_deducted_on_generation(self, client, test_db, test_user, test_session):
        """Test that credits are deducted on generation."""
        initial_credits = test_user.credits_remaining

        response = client.post(
            "/api/v1/generate",
            json={"prompt": "Create a funnel"},
            headers={"Authorization": f"Bearer {test_session}"},
        )
        assert response.status_code == 200

        # Refresh user
        test_db.refresh(test_user)
        assert test_user.credits_remaining == initial_credits - 1

    def test_no_credits_returns_402(self, client, test_db, test_user, test_session):
        """Test that 402 is returned when out of credits."""
        test_user.credits_remaining = 0
        test_db.commit()

        response = client.post(
            "/api/v1/generate",
            json={"prompt": "Create a funnel"},
            headers={"Authorization": f"Bearer {test_session}"},
        )
        assert response.status_code == 402
