"""Billing and subscription routes."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import User, PlanType
from backend.api.dependencies import CurrentUser
from backend.billing import (
    PLANS,
    get_plan,
    get_plan_limits,
)
from backend.billing.stripe_client import (
    create_customer,
    create_checkout_session,
    create_portal_session,
    get_subscription,
    cancel_subscription,
    reactivate_subscription,
    get_upcoming_invoice,
    list_invoices,
    verify_webhook_signature,
)
from backend.billing.usage import (
    get_usage_stats,
    get_usage_history,
    reset_monthly_credits,
    should_reset_credits,
)

router = APIRouter()


# Request/Response Models
class CreateCheckoutRequest(BaseModel):
    """Create checkout session request."""
    plan: Literal["pro"]
    billing_period: Literal["monthly", "yearly"] = "monthly"
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutResponse(BaseModel):
    """Checkout session response."""
    session_id: str
    url: str


class PortalResponse(BaseModel):
    """Customer portal response."""
    url: str


class PlanResponse(BaseModel):
    """Plan details response."""
    name: str
    price_monthly: int | None
    price_yearly: int | None
    features: list[str]
    limits: dict


class SubscriptionResponse(BaseModel):
    """Subscription details response."""
    plan: str
    status: str
    current_period_end: str | None
    cancel_at_period_end: bool
    credits_remaining: int
    credits_limit: int


class UsageStatsResponse(BaseModel):
    """Usage statistics response."""
    period_days: int
    total_credits_used: int
    by_action: dict[str, int]
    credits_remaining: int
    credits_limit: int
    reset_at: str | None


class InvoiceResponse(BaseModel):
    """Invoice response."""
    id: str
    number: str | None
    status: str
    amount_paid: int
    currency: str
    created: int
    invoice_pdf: str | None
    hosted_invoice_url: str | None


# Plans
@router.get("/plans")
async def list_plans():
    """List available subscription plans."""
    plans = []
    for plan_type, plan_data in PLANS.items():
        limits = plan_data["limits"]
        plans.append({
            "id": plan_type.value,
            "name": plan_data["name"],
            "price_monthly": plan_data["price_monthly"],
            "price_yearly": plan_data["price_yearly"],
            "features": plan_data["features"],
            "limits": {
                "generations_per_month": limits.generations_per_month,
                "variations_per_generation": limits.variations_per_generation,
                "export_formats": limits.export_formats,
                "custom_templates": limits.custom_templates,
                "api_access": limits.api_access,
                "team_members": limits.team_members,
            },
        })
    return {"plans": plans}


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan_details(plan_id: str):
    """Get details for a specific plan."""
    try:
        plan_type = PlanType(plan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    plan_data = get_plan(plan_type)
    limits = plan_data["limits"]

    return PlanResponse(
        name=plan_data["name"],
        price_monthly=plan_data["price_monthly"],
        price_yearly=plan_data["price_yearly"],
        features=plan_data["features"],
        limits={
            "generations_per_month": limits.generations_per_month,
            "variations_per_generation": limits.variations_per_generation,
            "export_formats": limits.export_formats,
            "custom_templates": limits.custom_templates,
            "api_access": limits.api_access,
        },
    )


# Checkout & Portal
@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for subscription."""
    if current_user.plan != PlanType.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active subscription. Use the billing portal to manage it.",
        )

    try:
        plan_type = PlanType(request.plan)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan",
        )

    # Create customer if needed
    if not current_user.stripe_customer_id:
        customer_id = create_customer(current_user)
        current_user.stripe_customer_id = customer_id
        db.commit()

    result = create_checkout_session(
        user=current_user,
        plan_type=plan_type,
        billing_period=request.billing_period,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )

    return CheckoutResponse(
        session_id=result["session_id"],
        url=result["url"],
    )


@router.post("/portal", response_model=PortalResponse)
async def create_customer_portal(
    current_user: CurrentUser,
    return_url: str | None = None,
):
    """Create a Stripe Customer Portal session."""
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Subscribe to a plan first.",
        )

    result = create_portal_session(
        customer_id=current_user.stripe_customer_id,
        return_url=return_url,
    )

    return PortalResponse(url=result["url"])


# Subscription Management
@router.get("/subscription", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get current subscription details."""
    # Check if credits need reset
    if should_reset_credits(current_user):
        reset_monthly_credits(db, current_user)

    limits = get_plan_limits(current_user.plan)

    # Get Stripe subscription details if exists
    subscription_details = None
    if current_user.stripe_subscription_id:
        subscription_details = get_subscription(current_user.stripe_subscription_id)

    return SubscriptionResponse(
        plan=current_user.plan.value,
        status=subscription_details["status"] if subscription_details else "active",
        current_period_end=datetime.fromtimestamp(
            subscription_details["current_period_end"]
        ).isoformat() if subscription_details and subscription_details.get("current_period_end") else None,
        cancel_at_period_end=subscription_details["cancel_at_period_end"] if subscription_details else False,
        credits_remaining=current_user.credits_remaining,
        credits_limit=limits.generations_per_month,
    )


@router.post("/subscription/cancel")
async def cancel_current_subscription(
    current_user: CurrentUser,
    at_period_end: bool = True,
):
    """Cancel current subscription."""
    if not current_user.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel",
        )

    result = cancel_subscription(
        subscription_id=current_user.stripe_subscription_id,
        at_period_end=at_period_end,
    )

    return {
        "status": "subscription_cancelled",
        "cancel_at_period_end": result["cancel_at_period_end"],
    }


@router.post("/subscription/reactivate")
async def reactivate_current_subscription(
    current_user: CurrentUser,
):
    """Reactivate a cancelled subscription."""
    if not current_user.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No subscription to reactivate",
        )

    result = reactivate_subscription(current_user.stripe_subscription_id)

    return {
        "status": "subscription_reactivated",
        "cancel_at_period_end": result["cancel_at_period_end"],
    }


# Usage & Invoices
@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    days: int = 30,
):
    """Get usage statistics."""
    stats = get_usage_stats(db, current_user, days)

    return UsageStatsResponse(
        period_days=stats["period_days"],
        total_credits_used=stats["total_credits_used"],
        by_action=stats["by_action"],
        credits_remaining=stats["credits_remaining"],
        credits_limit=stats["credits_limit"],
        reset_at=stats["reset_at"],
    )


@router.get("/usage/history")
async def get_usage_history_endpoint(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """Get usage history."""
    history = get_usage_history(db, current_user, limit, offset)
    return {"history": history}


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_user_invoices(
    current_user: CurrentUser,
    limit: int = 10,
):
    """List user's invoices."""
    if not current_user.stripe_customer_id:
        return []

    invoices = list_invoices(current_user.stripe_customer_id, limit)

    return [
        InvoiceResponse(
            id=inv["id"],
            number=inv["number"],
            status=inv["status"],
            amount_paid=inv["amount_paid"],
            currency=inv["currency"],
            created=inv["created"],
            invoice_pdf=inv["invoice_pdf"],
            hosted_invoice_url=inv["hosted_invoice_url"],
        )
        for inv in invoices
    ]


@router.get("/invoices/upcoming")
async def get_upcoming_invoice_endpoint(
    current_user: CurrentUser,
):
    """Get upcoming invoice."""
    if not current_user.stripe_customer_id:
        return {"upcoming_invoice": None}

    invoice = get_upcoming_invoice(current_user.stripe_customer_id)
    return {"upcoming_invoice": invoice}


# Webhooks
@router.post("/webhooks/stripe")
async def handle_stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(alias="Stripe-Signature"),
):
    """Handle Stripe webhooks."""
    payload = await request.body()

    try:
        event = verify_webhook_signature(payload, stripe_signature)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    event_type = event["type"]
    data = event["data"]["object"]

    # Handle subscription events
    if event_type == "customer.subscription.created":
        await _handle_subscription_created(db, data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data)
    elif event_type == "invoice.payment_succeeded":
        await _handle_payment_succeeded(db, data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)

    return {"received": True}


async def _handle_subscription_created(db: Session, subscription: dict):
    """Handle new subscription."""
    user_id = subscription.get("metadata", {}).get("user_id")
    if not user_id:
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    plan_type_str = subscription.get("metadata", {}).get("plan_type", "pro")
    try:
        plan_type = PlanType(plan_type_str)
    except ValueError:
        plan_type = PlanType.PRO

    user.stripe_subscription_id = subscription["id"]
    user.plan = plan_type

    # Reset credits for new plan
    reset_monthly_credits(db, user)


async def _handle_subscription_updated(db: Session, subscription: dict):
    """Handle subscription update."""
    user = db.query(User).filter(
        User.stripe_subscription_id == subscription["id"]
    ).first()

    if not user:
        return

    # Update plan if changed
    plan_type_str = subscription.get("metadata", {}).get("plan_type")
    if plan_type_str:
        try:
            user.plan = PlanType(plan_type_str)
            db.commit()
        except ValueError:
            pass


async def _handle_subscription_deleted(db: Session, subscription: dict):
    """Handle subscription cancellation."""
    user = db.query(User).filter(
        User.stripe_subscription_id == subscription["id"]
    ).first()

    if not user:
        return

    # Downgrade to free plan
    user.plan = PlanType.FREE
    user.stripe_subscription_id = None
    reset_monthly_credits(db, user)


async def _handle_payment_succeeded(db: Session, invoice: dict):
    """Handle successful payment - reset credits for new billing period."""
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    user = db.query(User).filter(
        User.stripe_customer_id == customer_id
    ).first()

    if not user:
        return

    # Reset credits for new billing period
    reset_monthly_credits(db, user)


async def _handle_payment_failed(db: Session, invoice: dict):
    """Handle failed payment."""
    # Log the failure, send notification, etc.
    # For now, we don't take immediate action - Stripe will retry
    pass
