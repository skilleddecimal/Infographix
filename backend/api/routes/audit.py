"""Audit log routes for Enterprise."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import User, MemberRole, AuditLog
from backend.api.dependencies import CurrentUser
from backend.api.routes.organizations import require_org_role


router = APIRouter()


class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    id: str
    action: str
    actor_id: str | None
    actor_email: str | None
    target_type: str | None
    target_id: str | None
    organization_id: str | None
    ip_address: str | None
    details: dict
    created_at: str


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


def audit_log_to_response(log: AuditLog) -> AuditLogResponse:
    """Convert AuditLog model to response."""
    return AuditLogResponse(
        id=log.id,
        action=log.action,
        actor_id=log.actor_id,
        actor_email=log.actor_email,
        target_type=log.target_type,
        target_id=log.target_id,
        organization_id=log.organization_id,
        ip_address=log.ip_address,
        details=log.details or {},
        created_at=log.created_at.isoformat(),
    )


@router.get("/{org_id}/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: str | None = None,
    actor_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    """
    List audit logs for an organization.

    Only owners and admins can view audit logs.
    """
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    query = db.query(AuditLog).filter(AuditLog.organization_id == org_id)

    if action:
        query = query.filter(AuditLog.action == action)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    if target_id:
        query = query.filter(AuditLog.target_id == target_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    # Get total count
    total = query.count()

    # Get paginated results
    offset = (page - 1) * page_size
    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()

    return AuditLogListResponse(
        items=[audit_log_to_response(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(logs)) < total,
    )


@router.get("/{org_id}/audit-logs/summary")
async def get_audit_summary(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90),
):
    """
    Get audit log summary for an organization.

    Returns action counts and recent security events.
    """
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    start_date = datetime.utcnow() - timedelta(days=days)

    # Get action counts
    from sqlalchemy import func
    action_counts = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .filter(AuditLog.organization_id == org_id)
        .filter(AuditLog.created_at >= start_date)
        .group_by(AuditLog.action)
        .all()
    )

    # Get security events
    security_actions = [
        "user.login_failed",
        "user.password_changed",
        "user.2fa_enabled",
        "user.2fa_disabled",
        "api.key_created",
        "api.key_revoked",
        "org.member_removed",
        "org.ownership_transferred",
    ]

    security_events = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == org_id)
        .filter(AuditLog.action.in_(security_actions))
        .filter(AuditLog.created_at >= start_date)
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )

    # Get unique actors
    unique_actors = (
        db.query(func.count(func.distinct(AuditLog.actor_id)))
        .filter(AuditLog.organization_id == org_id)
        .filter(AuditLog.created_at >= start_date)
        .scalar()
    )

    return {
        "period_days": days,
        "total_events": sum(count for _, count in action_counts),
        "unique_actors": unique_actors,
        "action_counts": {action: count for action, count in action_counts},
        "security_events": [audit_log_to_response(e) for e in security_events],
    }


@router.get("/{org_id}/audit-logs/export")
async def export_audit_logs(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    format: str = Query("json", pattern="^(json|csv)$"),
):
    """
    Export audit logs for compliance.

    Returns logs in JSON or CSV format.
    """
    require_org_role(db, current_user, org_id, [MemberRole.OWNER])

    query = db.query(AuditLog).filter(AuditLog.organization_id == org_id)

    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    logs = query.order_by(AuditLog.created_at.desc()).limit(10000).all()

    if format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "action", "actor_id", "actor_email", "target_type",
            "target_id", "ip_address", "created_at", "details"
        ])

        for log in logs:
            writer.writerow([
                log.id,
                log.action,
                log.actor_id,
                log.actor_email,
                log.target_type,
                log.target_id,
                log.ip_address,
                log.created_at.isoformat(),
                str(log.details or {}),
            ])

        from fastapi.responses import Response
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{org_id}.csv"}
        )

    return {
        "organization_id": org_id,
        "export_date": datetime.utcnow().isoformat(),
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "total_records": len(logs),
        "logs": [audit_log_to_response(log) for log in logs],
    }
