"""Database models for Infographix."""

import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.db.base import Base


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid4())


def generate_token() -> str:
    """Generate a secure token."""
    return secrets.token_urlsafe(32)


class PlanType(str, Enum):
    """Subscription plan types."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class GenerationStatus(str, Enum):
    """Generation job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MemberRole(str, Enum):
    """Organization member roles."""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    name = Column(String(255), nullable=True)

    # Subscription
    plan = Column(SQLEnum(PlanType), default=PlanType.FREE, nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    # Usage limits
    credits_remaining = Column(Integer, default=10)  # Free tier: 10 generations/month
    credits_reset_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)

    # OAuth
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    generations = relationship("Generation", back_populates="user", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")
    owned_organizations = relationship("Organization", back_populates="owner", cascade="all, delete-orphan")
    memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_pro(self) -> bool:
        """Check if user has Pro plan."""
        return self.plan in [PlanType.PRO, PlanType.ENTERPRISE]

    @property
    def is_enterprise(self) -> bool:
        """Check if user has Enterprise plan."""
        return self.plan == PlanType.ENTERPRISE

    def get_generation_limit(self) -> int:
        """Get monthly generation limit based on plan."""
        limits = {
            PlanType.FREE: 10,
            PlanType.PRO: 200,
            PlanType.ENTERPRISE: 999999,  # Unlimited
        }
        return limits.get(self.plan, 10)


class Session(Base):
    """User session model."""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    refresh_token_hash = Column(String(255), nullable=True, index=True)

    # Session info
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Expiration
    expires_at = Column(DateTime, nullable=False)
    refresh_expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session {self.id[:8]}>"

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at


class APIKey(Base):
    """API key model for programmatic access."""

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(255), nullable=False, index=True)
    name = Column(String(100), nullable=False)

    # Permissions
    scopes = Column(JSON, default=list)  # ["generate", "templates", "download"]

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    request_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<APIKey {self.name}>"


class Generation(Base):
    """Generation job model."""

    __tablename__ = "generations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Input
    prompt = Column(Text, nullable=False)
    content = Column(JSON, nullable=True)  # Optional content items
    brand_colors = Column(JSON, nullable=True)
    brand_fonts = Column(JSON, nullable=True)

    # Classification
    archetype = Column(String(50), nullable=True)
    archetype_confidence = Column(Float, nullable=True)

    # Generated output
    dsl = Column(JSON, nullable=True)
    style = Column(JSON, nullable=True)
    variations = Column(JSON, nullable=True)  # List of variation DSLs

    # Status
    status = Column(SQLEnum(GenerationStatus), default=GenerationStatus.PENDING)
    error_message = Column(Text, nullable=True)

    # Metadata
    processing_time_ms = Column(Integer, nullable=True)
    model_version = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="generations")
    downloads = relationship("Download", back_populates="generation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Generation {self.id[:8]} ({self.status})>"


class Download(Base):
    """Download record model."""

    __tablename__ = "downloads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    generation_id = Column(String(36), ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)

    # File info
    format = Column(String(10), nullable=False)  # pptx, pdf, png, svg
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)

    # Variation index (if applicable)
    variation_index = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    generation = relationship("Generation", back_populates="downloads")

    def __repr__(self) -> str:
        return f"<Download {self.format} for {self.generation_id[:8]}>"


class Template(Base):
    """Custom template model (Pro+)."""

    __tablename__ = "templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)

    # Template info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    archetype = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)

    # Template content
    dsl_template = Column(JSON, nullable=False)
    parameters = Column(JSON, nullable=True)  # Parameter schema
    thumbnail_url = Column(String(500), nullable=True)

    # Status
    is_public = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)  # For public templates

    # Usage stats
    use_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="templates")
    organization = relationship("Organization", back_populates="templates")

    def __repr__(self) -> str:
        return f"<Template {self.name}>"


class Organization(Base):
    """Organization model for Enterprise."""

    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Organization info
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)

    # Billing
    stripe_customer_id = Column(String(255), nullable=True)

    # Settings
    settings = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="owned_organizations")
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="organization")
    brand_guidelines = relationship("BrandGuideline", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"


class OrganizationMember(Base):
    """Organization membership model."""

    __tablename__ = "organization_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Role
    role = Column(SQLEnum(MemberRole), default=MemberRole.VIEWER, nullable=False)

    # Invitation
    invited_by_id = Column(String(36), nullable=True)
    invitation_token = Column(String(255), nullable=True)
    invitation_accepted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")

    # Constraints
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="unique_org_member"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember {self.user_id} in {self.organization_id}>"

    def can_edit(self) -> bool:
        """Check if member can edit content."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.EDITOR]

    def can_manage(self) -> bool:
        """Check if member can manage organization."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN]


class BrandGuideline(Base):
    """Brand guidelines model for Enterprise."""

    __tablename__ = "brand_guidelines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    # Brand identity
    name = Column(String(100), nullable=False, default="Default")

    # Colors
    primary_colors = Column(JSON, default=list)  # Required colors
    secondary_colors = Column(JSON, default=list)  # Optional colors
    forbidden_colors = Column(JSON, default=list)

    # Typography
    allowed_fonts = Column(JSON, default=list)
    heading_font = Column(String(100), nullable=True)
    body_font = Column(String(100), nullable=True)

    # Logo
    logo_url = Column(String(500), nullable=True)
    logo_placement = Column(String(50), nullable=True)  # top-left, top-right, etc.

    # Style constraints
    min_corner_radius = Column(Float, default=0)
    max_corner_radius = Column(Float, default=50)
    allow_shadows = Column(Boolean, default=True)
    allow_gradients = Column(Boolean, default=True)
    allow_glow = Column(Boolean, default=True)

    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="brand_guidelines")

    def __repr__(self) -> str:
        return f"<BrandGuideline {self.name}>"


class UsageRecord(Base):
    """Usage tracking model."""

    __tablename__ = "usage_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Action
    action = Column(String(50), nullable=False)  # generate, download, template_import
    credits_used = Column(Integer, default=1)

    # Context
    generation_id = Column(String(36), nullable=True)
    extra_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="usage_records")

    def __repr__(self) -> str:
        return f"<UsageRecord {self.action} by {self.user_id[:8]}>"
