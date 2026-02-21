"""Usage tracking and credit management."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.db.models import User, UsageRecord, PlanType
from backend.billing.plans import get_plan_limits


def record_usage(
    db: Session,
    user: User,
    action: str,
    credits_used: int = 1,
    generation_id: str | None = None,
    extra_data: dict | None = None,
) -> UsageRecord:
    """Record a usage event and deduct credits.

    Args:
        db: Database session.
        user: User performing the action.
        action: Action type (generate, download, template_import).
        credits_used: Number of credits to deduct.
        generation_id: Associated generation ID.
        extra_data: Additional metadata.

    Returns:
        Created UsageRecord.
    """
    # Create usage record
    record = UsageRecord(
        user_id=user.id,
        action=action,
        credits_used=credits_used,
        generation_id=generation_id,
        extra_data=extra_data,
    )
    db.add(record)

    # Deduct credits
    user.credits_remaining = max(0, user.credits_remaining - credits_used)

    db.commit()
    db.refresh(record)

    return record


def check_credits(user: User, required: int = 1) -> dict:
    """Check if user has sufficient credits.

    Args:
        user: User to check.
        required: Number of credits required.

    Returns:
        Dict with 'allowed', 'remaining', and optional 'upgrade_url'.
    """
    if user.plan == PlanType.ENTERPRISE:
        # Enterprise has unlimited credits
        return {
            "allowed": True,
            "remaining": 999999,
        }

    if user.credits_remaining >= required:
        return {
            "allowed": True,
            "remaining": user.credits_remaining,
        }

    return {
        "allowed": False,
        "remaining": user.credits_remaining,
        "required": required,
        "upgrade_url": "/pricing",
        "message": f"You need {required} credit(s) but only have {user.credits_remaining}. Upgrade your plan for more credits.",
    }


def reset_monthly_credits(db: Session, user: User) -> int:
    """Reset monthly credits based on plan.

    Args:
        db: Database session.
        user: User to reset credits for.

    Returns:
        New credit balance.
    """
    limits = get_plan_limits(user.plan)
    user.credits_remaining = limits.generations_per_month
    user.credits_reset_at = datetime.utcnow() + timedelta(days=30)
    db.commit()

    return user.credits_remaining


def get_usage_stats(
    db: Session,
    user: User,
    days: int = 30,
) -> dict:
    """Get usage statistics for a user.

    Args:
        db: Database session.
        user: User to get stats for.
        days: Number of days to look back.

    Returns:
        Usage statistics dict.
    """
    since = datetime.utcnow() - timedelta(days=days)

    records = db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
        UsageRecord.created_at >= since,
    ).all()

    # Aggregate by action
    by_action: dict[str, int] = {}
    total_credits = 0

    for record in records:
        action = record.action
        by_action[action] = by_action.get(action, 0) + record.credits_used
        total_credits += record.credits_used

    # Get plan limits
    limits = get_plan_limits(user.plan)

    return {
        "period_days": days,
        "total_credits_used": total_credits,
        "by_action": by_action,
        "credits_remaining": user.credits_remaining,
        "credits_limit": limits.generations_per_month,
        "reset_at": user.credits_reset_at.isoformat() if user.credits_reset_at else None,
    }


def get_usage_history(
    db: Session,
    user: User,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Get usage history for a user.

    Args:
        db: Database session.
        user: User to get history for.
        limit: Maximum records to return.
        offset: Number of records to skip.

    Returns:
        List of usage record dicts.
    """
    records = db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
    ).order_by(
        UsageRecord.created_at.desc()
    ).offset(offset).limit(limit).all()

    return [
        {
            "id": record.id,
            "action": record.action,
            "credits_used": record.credits_used,
            "generation_id": record.generation_id,
            "created_at": record.created_at.isoformat(),
        }
        for record in records
    ]


def should_reset_credits(user: User) -> bool:
    """Check if user's credits should be reset.

    Args:
        user: User to check.

    Returns:
        True if credits should be reset.
    """
    if not user.credits_reset_at:
        return True

    return datetime.utcnow() >= user.credits_reset_at
