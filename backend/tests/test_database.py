"""Tests for database models and operations."""

import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.base import Base
from backend.db.models import (
    User,
    Session,
    APIKey,
    Generation,
    Download,
    Template,
    Organization,
    OrganizationMember,
    BrandGuideline,
    UsageRecord,
    PlanType,
    GenerationStatus,
    MemberRole,
)


# Test database setup
@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, db_session):
        """Test creating a user."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            name="Test User",
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.plan == PlanType.FREE
        assert user.credits_remaining == 10

    def test_user_plan_check(self, db_session):
        """Test user plan checking."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        assert not user.is_pro
        assert not user.is_enterprise

        user.plan = PlanType.PRO
        assert user.is_pro
        assert not user.is_enterprise

        user.plan = PlanType.ENTERPRISE
        assert user.is_pro
        assert user.is_enterprise

    def test_user_generation_limit(self, db_session):
        """Test user generation limit calculation."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        assert user.get_generation_limit() == 10

        user.plan = PlanType.PRO
        assert user.get_generation_limit() == 200

        user.plan = PlanType.ENTERPRISE
        assert user.get_generation_limit() == 999999


class TestSessionModel:
    """Tests for Session model."""

    def test_create_session(self, db_session):
        """Test creating a session."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        session = Session(
            user_id=user.id,
            token_hash="hashed_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db_session.add(session)
        db_session.commit()

        assert session.id is not None
        assert session.user_id == user.id
        assert not session.is_expired

    def test_session_expiration(self, db_session):
        """Test session expiration check."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        session = Session(
            user_id=user.id,
            token_hash="hashed_token",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        db_session.add(session)
        db_session.commit()

        assert session.is_expired


class TestGenerationModel:
    """Tests for Generation model."""

    def test_create_generation(self, db_session):
        """Test creating a generation."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        generation = Generation(
            user_id=user.id,
            prompt="Create a sales funnel",
            status=GenerationStatus.PENDING,
        )
        db_session.add(generation)
        db_session.commit()

        assert generation.id is not None
        assert generation.status == GenerationStatus.PENDING
        assert generation.archetype is None

    def test_generation_with_dsl(self, db_session):
        """Test generation with DSL data."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        dsl = {
            "shapes": [
                {"id": "1", "type": "rect"},
            ],
            "theme": {"accent1": "#0D9488"},
        }

        generation = Generation(
            user_id=user.id,
            prompt="Create a funnel",
            archetype="funnel",
            dsl=dsl,
            status=GenerationStatus.COMPLETED,
        )
        db_session.add(generation)
        db_session.commit()

        # Reload and verify JSON is preserved
        db_session.refresh(generation)
        assert generation.dsl == dsl
        assert generation.dsl["shapes"][0]["id"] == "1"


class TestTemplateModel:
    """Tests for Template model."""

    def test_create_template(self, db_session):
        """Test creating a template."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        template = Template(
            user_id=user.id,
            name="My Funnel",
            archetype="funnel",
            dsl_template={"shapes": []},
        )
        db_session.add(template)
        db_session.commit()

        assert template.id is not None
        assert template.use_count == 0

    def test_template_use_count(self, db_session):
        """Test template use count increment."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        template = Template(
            user_id=user.id,
            name="My Template",
            dsl_template={},
        )
        db_session.add(template)
        db_session.commit()

        template.use_count += 1
        db_session.commit()

        assert template.use_count == 1


class TestOrganizationModel:
    """Tests for Organization model."""

    def test_create_organization(self, db_session):
        """Test creating an organization."""
        user = User(email="owner@example.com")
        db_session.add(user)
        db_session.commit()

        org = Organization(
            owner_id=user.id,
            name="Acme Corp",
            slug="acme-corp",
        )
        db_session.add(org)
        db_session.commit()

        assert org.id is not None
        assert org.owner_id == user.id

    def test_organization_members(self, db_session):
        """Test organization membership."""
        owner = User(email="owner@example.com")
        member = User(email="member@example.com")
        db_session.add_all([owner, member])
        db_session.commit()

        org = Organization(
            owner_id=owner.id,
            name="Acme Corp",
            slug="acme-corp",
        )
        db_session.add(org)
        db_session.commit()

        membership = OrganizationMember(
            organization_id=org.id,
            user_id=member.id,
            role=MemberRole.EDITOR,
        )
        db_session.add(membership)
        db_session.commit()

        assert membership.can_edit()
        assert not membership.can_manage()


class TestBrandGuidelineModel:
    """Tests for BrandGuideline model."""

    def test_create_brand_guideline(self, db_session):
        """Test creating brand guidelines."""
        user = User(email="owner@example.com")
        db_session.add(user)
        db_session.commit()

        org = Organization(
            owner_id=user.id,
            name="Acme Corp",
            slug="acme-corp",
        )
        db_session.add(org)
        db_session.commit()

        guideline = BrandGuideline(
            organization_id=org.id,
            name="Corporate Style",
            primary_colors=["#0D9488", "#14B8A6"],
            allowed_fonts=["Inter", "Roboto"],
        )
        db_session.add(guideline)
        db_session.commit()

        assert guideline.id is not None
        assert len(guideline.primary_colors) == 2


class TestUsageRecordModel:
    """Tests for UsageRecord model."""

    def test_create_usage_record(self, db_session):
        """Test creating usage record."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        record = UsageRecord(
            user_id=user.id,
            action="generate",
            credits_used=1,
        )
        db_session.add(record)
        db_session.commit()

        assert record.id is not None
        assert record.action == "generate"


class TestCascadeDeletes:
    """Tests for cascade delete behavior."""

    def test_user_cascade_delete(self, db_session):
        """Test that deleting user cascades to related records."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        # Create related records
        session = Session(
            user_id=user.id,
            token_hash="token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        generation = Generation(
            user_id=user.id,
            prompt="Test",
            status=GenerationStatus.PENDING,
        )
        db_session.add_all([session, generation])
        db_session.commit()

        # Delete user
        db_session.delete(user)
        db_session.commit()

        # Verify cascade
        assert db_session.query(Session).filter(Session.user_id == user.id).count() == 0
        assert db_session.query(Generation).filter(Generation.user_id == user.id).count() == 0
