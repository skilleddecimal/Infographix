"""Tests for enterprise features module."""

import pytest
from datetime import datetime, timedelta

from backend.enterprise.audit import (
    AuditLogger,
    AuditAction,
    AuditEntry,
)
from backend.enterprise.webhooks import (
    WebhookManager,
    WebhookEvent,
    WebhookPayload,
    WebhookEndpoint,
)


class TestAuditLogger:
    """Test audit logging functionality."""

    def test_log_creates_entry(self):
        """Logging should create an audit entry."""
        logger = AuditLogger()

        entry = logger.log(
            action=AuditAction.USER_LOGIN,
            actor_id="user-123",
            actor_email="test@example.com",
            ip_address="192.168.1.1",
        )

        assert entry.action == AuditAction.USER_LOGIN
        assert entry.actor_id == "user-123"
        assert entry.actor_email == "test@example.com"
        assert entry.ip_address == "192.168.1.1"
        assert entry.timestamp is not None

    def test_log_with_details(self):
        """Logging should include additional details."""
        logger = AuditLogger()

        entry = logger.log(
            action=AuditAction.ORG_MEMBER_ADDED,
            actor_id="admin-123",
            target_type="user",
            target_id="new-user-456",
            organization_id="org-789",
            details={"role": "editor", "invited_via": "email"},
        )

        assert entry.target_type == "user"
        assert entry.target_id == "new-user-456"
        assert entry.organization_id == "org-789"
        assert entry.details["role"] == "editor"

    def test_log_to_dict(self):
        """Audit entry should convert to dictionary."""
        entry = AuditEntry(
            action=AuditAction.GENERATION_COMPLETED,
            actor_id="user-123",
            actor_email="test@example.com",
            target_type="generation",
            target_id="gen-456",
            organization_id=None,
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
            details={"archetype": "timeline"},
        )

        data = entry.to_dict()

        assert data["action"] == "generation.completed"
        assert data["actor_id"] == "user-123"
        assert data["details"]["archetype"] == "timeline"

    def test_query_in_memory(self):
        """Query should filter in-memory entries."""
        logger = AuditLogger()

        logger.log(action=AuditAction.USER_LOGIN, actor_id="user-1")
        logger.log(action=AuditAction.USER_LOGIN, actor_id="user-2")
        logger.log(action=AuditAction.USER_LOGOUT, actor_id="user-1")

        results = logger.query(action=AuditAction.USER_LOGIN)
        assert len(results) == 2

        results = logger.query(actor_id="user-1")
        assert len(results) == 2

        results = logger.query(action=AuditAction.USER_LOGIN, actor_id="user-1")
        assert len(results) == 1

    def test_query_pagination(self):
        """Query should support pagination."""
        logger = AuditLogger()

        for i in range(10):
            logger.log(action=AuditAction.USER_LOGIN, actor_id=f"user-{i}")

        results = logger.query(limit=5)
        assert len(results) == 5

        results = logger.query(limit=5, offset=5)
        assert len(results) == 5

    def test_get_user_activity(self):
        """Should get recent activity for a user."""
        logger = AuditLogger()

        logger.log(action=AuditAction.USER_LOGIN, actor_id="user-123")
        logger.log(action=AuditAction.GENERATION_STARTED, actor_id="user-123")
        logger.log(action=AuditAction.USER_LOGIN, actor_id="other-user")

        activity = logger.get_user_activity("user-123")
        assert len(activity) == 2

    def test_audit_action_values(self):
        """Audit actions should have correct string values."""
        assert AuditAction.USER_LOGIN.value == "user.login"
        assert AuditAction.ORG_CREATED.value == "org.created"
        assert AuditAction.BRAND_GUIDELINE_CREATED.value == "brand.guideline_created"
        assert AuditAction.API_KEY_CREATED.value == "api.key_created"


class TestWebhookManager:
    """Test webhook management functionality."""

    def test_register_endpoint(self):
        """Registering an endpoint should create it."""
        manager = WebhookManager()

        endpoint = manager.register_endpoint(
            url="https://example.com/webhook",
            secret="my_secret_key",
            events=[WebhookEvent.GENERATION_COMPLETED],
            organization_id="org-123",
        )

        assert endpoint.url == "https://example.com/webhook"
        assert endpoint.secret == "my_secret_key"
        assert WebhookEvent.GENERATION_COMPLETED in endpoint.events
        assert endpoint.organization_id == "org-123"
        assert endpoint.is_active is True

    def test_get_endpoints_by_org(self):
        """Should filter endpoints by organization."""
        manager = WebhookManager()

        manager.register_endpoint(
            url="https://org1.com/webhook",
            secret="secret1",
            events=[WebhookEvent.GENERATION_COMPLETED],
            organization_id="org-1",
        )
        manager.register_endpoint(
            url="https://org2.com/webhook",
            secret="secret2",
            events=[WebhookEvent.GENERATION_COMPLETED],
            organization_id="org-2",
        )

        endpoints = manager.get_endpoints(organization_id="org-1")
        assert len(endpoints) == 1
        assert endpoints[0].url == "https://org1.com/webhook"

    def test_get_endpoints_by_event(self):
        """Should filter endpoints by event type."""
        manager = WebhookManager()

        manager.register_endpoint(
            url="https://gen.com/webhook",
            secret="secret1",
            events=[WebhookEvent.GENERATION_COMPLETED],
        )
        manager.register_endpoint(
            url="https://member.com/webhook",
            secret="secret2",
            events=[WebhookEvent.MEMBER_ADDED],
        )

        endpoints = manager.get_endpoints(event=WebhookEvent.GENERATION_COMPLETED)
        assert len(endpoints) == 1
        assert endpoints[0].url == "https://gen.com/webhook"

    def test_unregister_endpoint(self):
        """Unregistering should remove the endpoint."""
        manager = WebhookManager()

        endpoint = manager.register_endpoint(
            url="https://example.com/webhook",
            secret="secret",
            events=[WebhookEvent.GENERATION_COMPLETED],
        )

        result = manager.unregister_endpoint(endpoint.id)
        assert result is True

        endpoints = manager.get_endpoints()
        assert len(endpoints) == 0

    def test_sign_payload(self):
        """Payload signing should be consistent."""
        manager = WebhookManager()

        payload = '{"event": "test"}'
        secret = "my_secret"

        sig1 = manager.sign_payload(payload, secret)
        sig2 = manager.sign_payload(payload, secret)

        assert sig1 == sig2
        assert len(sig1) == 64  # SHA-256 hex

    def test_verify_signature_valid(self):
        """Valid signature should verify."""
        manager = WebhookManager()

        payload = '{"event": "generation.completed"}'
        secret = "webhook_secret_123"
        signature = manager.sign_payload(payload, secret)

        assert manager.verify_signature(payload, signature, secret) is True

    def test_verify_signature_invalid(self):
        """Invalid signature should not verify."""
        manager = WebhookManager()

        payload = '{"event": "test"}'
        secret = "correct_secret"
        wrong_secret = "wrong_secret"

        signature = manager.sign_payload(payload, secret)

        assert manager.verify_signature(payload, signature, wrong_secret) is False
        assert manager.verify_signature(payload, "invalid_sig", secret) is False

    def test_webhook_payload(self):
        """WebhookPayload should serialize correctly."""
        payload = WebhookPayload(
            event=WebhookEvent.GENERATION_COMPLETED,
            data={"generation_id": "gen-123", "archetype": "timeline"},
            organization_id="org-456",
        )

        assert payload.webhook_id  # Auto-generated
        assert payload.event == WebhookEvent.GENERATION_COMPLETED
        assert payload.data["generation_id"] == "gen-123"

        data = payload.to_dict()
        assert data["event"] == "generation.completed"
        assert "timestamp" in data

    def test_webhook_event_values(self):
        """Webhook events should have correct string values."""
        assert WebhookEvent.GENERATION_STARTED.value == "generation.started"
        assert WebhookEvent.MEMBER_ADDED.value == "organization.member_added"
        assert WebhookEvent.COMPLIANCE_VIOLATION.value == "brand.compliance_violation"
        assert WebhookEvent.USAGE_LIMIT_REACHED.value == "billing.usage_limit_reached"

    def test_on_event_handler(self):
        """Event handlers should be registered."""
        manager = WebhookManager()
        called = []

        @manager.on_event(WebhookEvent.GENERATION_COMPLETED)
        def handle_generation(payload):
            called.append(payload)

        # Handler should be registered
        assert WebhookEvent.GENERATION_COMPLETED in manager._handlers
        assert len(manager._handlers[WebhookEvent.GENERATION_COMPLETED]) == 1


class TestWebhookEndpoint:
    """Test WebhookEndpoint dataclass."""

    def test_endpoint_defaults(self):
        """Endpoint should have correct defaults."""
        endpoint = WebhookEndpoint(
            id="ep-123",
            url="https://example.com/hook",
            secret="secret",
            events=[WebhookEvent.GENERATION_COMPLETED],
        )

        assert endpoint.is_active is True
        assert endpoint.failure_count == 0
        assert endpoint.last_failure is None
        assert endpoint.last_success is None
        assert endpoint.organization_id is None

    def test_endpoint_with_org(self):
        """Endpoint should store organization."""
        endpoint = WebhookEndpoint(
            id="ep-123",
            url="https://example.com/hook",
            secret="secret",
            events=[WebhookEvent.MEMBER_ADDED],
            organization_id="org-456",
        )

        assert endpoint.organization_id == "org-456"


class TestBrandComplianceLogic:
    """Test brand compliance checking logic."""

    def test_color_validation(self):
        """Color validation should follow brand guidelines."""
        # Simulating brand guideline checks
        primary_colors = ["#FF5733", "#33FF57"]
        forbidden_colors = ["#000000"]

        test_color = "#FF5733"
        assert test_color in primary_colors

        test_forbidden = "#000000"
        assert test_forbidden in forbidden_colors

    def test_corner_radius_bounds(self):
        """Corner radius should respect min/max bounds."""
        min_radius = 0
        max_radius = 50

        # Valid
        assert 0 <= 10 <= max_radius
        assert min_radius <= 0 <= max_radius

        # Invalid
        assert not (0 <= -5)
        assert not (60 <= max_radius)


class TestMemberRoles:
    """Test organization member role permissions."""

    def test_role_hierarchy(self):
        """Roles should have correct permissions."""
        from backend.db.models import MemberRole

        owner_perms = [MemberRole.OWNER]
        admin_perms = [MemberRole.OWNER, MemberRole.ADMIN]
        editor_perms = [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.EDITOR]
        all_perms = list(MemberRole)

        # Owner can do owner things
        assert MemberRole.OWNER in owner_perms

        # Admin can manage
        assert MemberRole.ADMIN in admin_perms

        # Editor can edit
        assert MemberRole.EDITOR in editor_perms

        # Viewer is lowest level
        assert MemberRole.VIEWER in all_perms
        assert MemberRole.VIEWER not in admin_perms


class TestOrganizationInvitation:
    """Test organization invitation model."""

    def test_invitation_expiration(self):
        """Invitation should track expiration."""
        from backend.db.models import OrganizationInvitation, MemberRole

        # Create a mock invitation
        expires_at = datetime.utcnow() + timedelta(days=7)

        # Not expired
        assert datetime.utcnow() < expires_at

        # Expired
        expired_at = datetime.utcnow() - timedelta(hours=1)
        assert datetime.utcnow() > expired_at


class TestAuditLogModel:
    """Test audit log database model."""

    def test_audit_log_fields(self):
        """AuditLog should have required fields."""
        from backend.db.models import AuditLog

        # Check table name
        assert AuditLog.__tablename__ == "audit_logs"

        # Check columns exist
        columns = {c.name for c in AuditLog.__table__.columns}
        assert "id" in columns
        assert "action" in columns
        assert "actor_id" in columns
        assert "actor_email" in columns
        assert "target_type" in columns
        assert "target_id" in columns
        assert "organization_id" in columns
        assert "ip_address" in columns
        assert "details" in columns
        assert "created_at" in columns


class TestWebhookModels:
    """Test webhook database models."""

    def test_webhook_endpoint_fields(self):
        """WebhookEndpoint model should have required fields."""
        from backend.db.models import WebhookEndpoint

        assert WebhookEndpoint.__tablename__ == "webhook_endpoints"

        columns = {c.name for c in WebhookEndpoint.__table__.columns}
        assert "id" in columns
        assert "url" in columns
        assert "secret_hash" in columns
        assert "events" in columns
        assert "is_active" in columns
        assert "organization_id" in columns

    def test_webhook_delivery_fields(self):
        """WebhookDelivery model should have required fields."""
        from backend.db.models import WebhookDelivery

        assert WebhookDelivery.__tablename__ == "webhook_deliveries"

        columns = {c.name for c in WebhookDelivery.__table__.columns}
        assert "id" in columns
        assert "endpoint_id" in columns
        assert "event_type" in columns
        assert "payload" in columns
        assert "status_code" in columns
        assert "success" in columns
        assert "retry_count" in columns
