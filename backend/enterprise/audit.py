"""Enterprise audit logging system."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
import json

from sqlalchemy.orm import Session


class AuditAction(str, Enum):
    """Types of auditable actions."""

    # User actions
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_LOGIN_FAILED = "user.login_failed"
    USER_PASSWORD_CHANGED = "user.password_changed"
    USER_PASSWORD_RESET = "user.password_reset"
    USER_2FA_ENABLED = "user.2fa_enabled"
    USER_2FA_DISABLED = "user.2fa_disabled"

    # Organization actions
    ORG_CREATED = "org.created"
    ORG_UPDATED = "org.updated"
    ORG_DELETED = "org.deleted"
    ORG_MEMBER_ADDED = "org.member_added"
    ORG_MEMBER_REMOVED = "org.member_removed"
    ORG_MEMBER_ROLE_CHANGED = "org.member_role_changed"
    ORG_INVITATION_SENT = "org.invitation_sent"
    ORG_INVITATION_ACCEPTED = "org.invitation_accepted"
    ORG_OWNERSHIP_TRANSFERRED = "org.ownership_transferred"

    # Brand guidelines actions
    BRAND_GUIDELINE_CREATED = "brand.guideline_created"
    BRAND_GUIDELINE_UPDATED = "brand.guideline_updated"
    BRAND_GUIDELINE_DELETED = "brand.guideline_deleted"
    BRAND_COMPLIANCE_CHECK = "brand.compliance_check"

    # Generation actions
    GENERATION_STARTED = "generation.started"
    GENERATION_COMPLETED = "generation.completed"
    GENERATION_FAILED = "generation.failed"
    GENERATION_EXPORTED = "generation.exported"

    # Template actions
    TEMPLATE_CREATED = "template.created"
    TEMPLATE_UPDATED = "template.updated"
    TEMPLATE_DELETED = "template.deleted"
    TEMPLATE_SHARED = "template.shared"

    # API actions
    API_KEY_CREATED = "api.key_created"
    API_KEY_REVOKED = "api.key_revoked"
    API_REQUEST = "api.request"

    # Billing actions
    SUBSCRIPTION_CREATED = "billing.subscription_created"
    SUBSCRIPTION_UPDATED = "billing.subscription_updated"
    SUBSCRIPTION_CANCELLED = "billing.subscription_cancelled"
    PAYMENT_SUCCEEDED = "billing.payment_succeeded"
    PAYMENT_FAILED = "billing.payment_failed"


@dataclass
class AuditEntry:
    """Represents a single audit log entry."""

    action: AuditAction
    actor_id: str | None  # User who performed the action
    actor_email: str | None
    target_type: str | None  # Type of resource affected
    target_id: str | None  # ID of resource affected
    organization_id: str | None
    ip_address: str | None
    user_agent: str | None
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "action": self.action.value,
            "actor_id": self.actor_id,
            "actor_email": self.actor_email,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "organization_id": self.organization_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class AuditLogger:
    """
    Enterprise audit logging system.

    Logs all significant actions for compliance and security purposes.
    Supports multiple storage backends (database, file, external services).
    """

    def __init__(
        self,
        db: Session | None = None,
        log_to_file: bool = False,
        log_file_path: str = "audit.log",
    ):
        self.db = db
        self.log_to_file = log_to_file
        self.log_file_path = log_file_path
        self._entries: list[AuditEntry] = []  # In-memory buffer

    def log(
        self,
        action: AuditAction,
        actor_id: str | None = None,
        actor_email: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        organization_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
    ) -> AuditEntry:
        """
        Log an audit event.

        Args:
            action: The type of action being logged
            actor_id: ID of the user performing the action
            actor_email: Email of the user performing the action
            target_type: Type of resource affected (user, org, generation, etc.)
            target_id: ID of the affected resource
            organization_id: Organization context if applicable
            ip_address: Client IP address
            user_agent: Client user agent string
            details: Additional details about the action

        Returns:
            The created audit entry
        """
        entry = AuditEntry(
            action=action,
            actor_id=actor_id,
            actor_email=actor_email,
            target_type=target_type,
            target_id=target_id,
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )

        # Store in memory buffer
        self._entries.append(entry)

        # Store to database if available
        if self.db:
            self._store_to_db(entry)

        # Store to file if enabled
        if self.log_to_file:
            self._store_to_file(entry)

        return entry

    def _store_to_db(self, entry: AuditEntry) -> None:
        """Store audit entry to database."""
        # Import here to avoid circular imports
        from backend.db.models import AuditLog

        audit_log = AuditLog(
            action=entry.action.value,
            actor_id=entry.actor_id,
            actor_email=entry.actor_email,
            target_type=entry.target_type,
            target_id=entry.target_id,
            organization_id=entry.organization_id,
            ip_address=entry.ip_address,
            user_agent=entry.user_agent,
            details=entry.details,
            created_at=entry.timestamp,
        )
        self.db.add(audit_log)
        # Note: Caller should commit the transaction

    def _store_to_file(self, entry: AuditEntry) -> None:
        """Append audit entry to log file."""
        with open(self.log_file_path, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def query(
        self,
        action: AuditAction | None = None,
        actor_id: str | None = None,
        organization_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Query audit logs from database.

        Args:
            action: Filter by action type
            actor_id: Filter by actor
            organization_id: Filter by organization
            target_type: Filter by target type
            target_id: Filter by target ID
            start_date: Filter entries after this date
            end_date: Filter entries before this date
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of audit log entries as dictionaries
        """
        if not self.db:
            # Return from in-memory buffer if no database
            results = []
            for entry in self._entries:
                if action and entry.action != action:
                    continue
                if actor_id and entry.actor_id != actor_id:
                    continue
                if organization_id and entry.organization_id != organization_id:
                    continue
                if target_type and entry.target_type != target_type:
                    continue
                if target_id and entry.target_id != target_id:
                    continue
                if start_date and entry.timestamp < start_date:
                    continue
                if end_date and entry.timestamp > end_date:
                    continue
                results.append(entry.to_dict())

            return results[offset:offset + limit]

        # Query from database
        from backend.db.models import AuditLog

        query = self.db.query(AuditLog)

        if action:
            query = query.filter(AuditLog.action == action.value)
        if actor_id:
            query = query.filter(AuditLog.actor_id == actor_id)
        if organization_id:
            query = query.filter(AuditLog.organization_id == organization_id)
        if target_type:
            query = query.filter(AuditLog.target_type == target_type)
        if target_id:
            query = query.filter(AuditLog.target_id == target_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

        return [
            {
                "id": log.id,
                "action": log.action,
                "actor_id": log.actor_id,
                "actor_email": log.actor_email,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "organization_id": log.organization_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "details": log.details,
                "timestamp": log.created_at.isoformat(),
            }
            for log in logs
        ]

    def get_user_activity(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100,
    ) -> list[dict]:
        """Get recent activity for a specific user."""
        start_date = datetime.utcnow() - __import__("datetime").timedelta(days=days)
        return self.query(
            actor_id=user_id,
            start_date=start_date,
            limit=limit,
        )

    def get_organization_activity(
        self,
        organization_id: str,
        days: int = 30,
        limit: int = 100,
    ) -> list[dict]:
        """Get recent activity for an organization."""
        start_date = datetime.utcnow() - __import__("datetime").timedelta(days=days)
        return self.query(
            organization_id=organization_id,
            start_date=start_date,
            limit=limit,
        )

    def get_security_events(
        self,
        organization_id: str | None = None,
        days: int = 7,
    ) -> list[dict]:
        """Get security-related events (login failures, password changes, etc.)."""
        security_actions = [
            AuditAction.USER_LOGIN_FAILED,
            AuditAction.USER_PASSWORD_CHANGED,
            AuditAction.USER_PASSWORD_RESET,
            AuditAction.USER_2FA_ENABLED,
            AuditAction.USER_2FA_DISABLED,
            AuditAction.API_KEY_CREATED,
            AuditAction.API_KEY_REVOKED,
        ]

        results = []
        for action in security_actions:
            results.extend(
                self.query(
                    action=action,
                    organization_id=organization_id,
                    start_date=datetime.utcnow() - __import__("datetime").timedelta(days=days),
                    limit=50,
                )
            )

        # Sort by timestamp
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:100]
