"""Stripe API client for billing operations."""

import os
from typing import Optional

import stripe

from backend.db.models import User, PlanType
from backend.billing.plans import get_stripe_price_id

# Initialize Stripe with API key from environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


def create_customer(user: User) -> str:
    """Create a Stripe customer for a user.

    Args:
        user: User to create customer for.

    Returns:
        Stripe customer ID.
    """
    customer = stripe.Customer.create(
        email=user.email,
        name=user.name,
        metadata={
            "user_id": user.id,
        },
    )
    return customer.id


def create_checkout_session(
    user: User,
    plan_type: PlanType,
    billing_period: str = "monthly",
    success_url: str = "",
    cancel_url: str = "",
) -> dict:
    """Create a Stripe Checkout session for subscription.

    Args:
        user: User to create session for.
        plan_type: Plan to subscribe to.
        billing_period: 'monthly' or 'yearly'.
        success_url: URL to redirect on success.
        cancel_url: URL to redirect on cancel.

    Returns:
        Dict with session_id and url.
    """
    price_id = get_stripe_price_id(plan_type, billing_period)
    if not price_id:
        raise ValueError(f"No Stripe price ID for {plan_type} {billing_period}")

    # Ensure customer exists
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer_id = create_customer(user)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            },
        ],
        mode="subscription",
        success_url=success_url or "https://infographix.com/billing/success",
        cancel_url=cancel_url or "https://infographix.com/pricing",
        metadata={
            "user_id": user.id,
            "plan_type": plan_type.value,
        },
        subscription_data={
            "metadata": {
                "user_id": user.id,
                "plan_type": plan_type.value,
            },
        },
    )

    return {
        "session_id": session.id,
        "url": session.url,
    }


def create_portal_session(
    customer_id: str,
    return_url: str = "",
) -> dict:
    """Create a Stripe Customer Portal session.

    Args:
        customer_id: Stripe customer ID.
        return_url: URL to return to after portal.

    Returns:
        Dict with url.
    """
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url or "https://infographix.com/settings/billing",
    )

    return {
        "url": session.url,
    }


def get_subscription(subscription_id: str) -> dict | None:
    """Get subscription details.

    Args:
        subscription_id: Stripe subscription ID.

    Returns:
        Subscription dict or None.
    """
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        return {
            "id": subscription.id,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "canceled_at": subscription.canceled_at,
            "plan_id": subscription.items.data[0].price.id if subscription.items.data else None,
        }
    except stripe.error.InvalidRequestError:
        return None


def cancel_subscription(
    subscription_id: str,
    at_period_end: bool = True,
) -> dict:
    """Cancel a subscription.

    Args:
        subscription_id: Stripe subscription ID.
        at_period_end: If True, cancel at end of billing period.

    Returns:
        Updated subscription dict.
    """
    if at_period_end:
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
        )
    else:
        subscription = stripe.Subscription.cancel(subscription_id)

    return {
        "id": subscription.id,
        "status": subscription.status,
        "cancel_at_period_end": subscription.cancel_at_period_end,
    }


def reactivate_subscription(subscription_id: str) -> dict:
    """Reactivate a subscription that was set to cancel.

    Args:
        subscription_id: Stripe subscription ID.

    Returns:
        Updated subscription dict.
    """
    subscription = stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=False,
    )

    return {
        "id": subscription.id,
        "status": subscription.status,
        "cancel_at_period_end": subscription.cancel_at_period_end,
    }


def get_upcoming_invoice(customer_id: str) -> dict | None:
    """Get upcoming invoice for a customer.

    Args:
        customer_id: Stripe customer ID.

    Returns:
        Invoice details or None.
    """
    try:
        invoice = stripe.Invoice.upcoming(customer=customer_id)
        return {
            "amount_due": invoice.amount_due,
            "currency": invoice.currency,
            "period_start": invoice.period_start,
            "period_end": invoice.period_end,
            "lines": [
                {
                    "description": line.description,
                    "amount": line.amount,
                }
                for line in invoice.lines.data
            ],
        }
    except stripe.error.InvalidRequestError:
        return None


def list_invoices(
    customer_id: str,
    limit: int = 10,
) -> list[dict]:
    """List invoices for a customer.

    Args:
        customer_id: Stripe customer ID.
        limit: Maximum number of invoices to return.

    Returns:
        List of invoice dicts.
    """
    invoices = stripe.Invoice.list(customer=customer_id, limit=limit)

    return [
        {
            "id": inv.id,
            "number": inv.number,
            "status": inv.status,
            "amount_paid": inv.amount_paid,
            "currency": inv.currency,
            "created": inv.created,
            "invoice_pdf": inv.invoice_pdf,
            "hosted_invoice_url": inv.hosted_invoice_url,
        }
        for inv in invoices.data
    ]


def verify_webhook_signature(payload: bytes, signature: str) -> dict:
    """Verify Stripe webhook signature and return event.

    Args:
        payload: Raw request body.
        signature: Stripe-Signature header.

    Returns:
        Stripe event dict.

    Raises:
        ValueError: If signature is invalid.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            STRIPE_WEBHOOK_SECRET,
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Invalid webhook signature: {e}")
