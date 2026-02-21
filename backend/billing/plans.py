"""Subscription plans configuration."""

from typing import NamedTuple
from backend.db.models import PlanType


class PlanLimits(NamedTuple):
    """Plan resource limits."""
    generations_per_month: int
    variations_per_generation: int
    export_formats: list[str]
    custom_templates: bool
    api_access: bool
    team_members: int
    priority_support: bool


# Plan definitions
PLANS = {
    PlanType.FREE: {
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "stripe_price_id_monthly": None,
        "stripe_price_id_yearly": None,
        "features": [
            "10 generations per month",
            "2 variations per generation",
            "PPTX export only",
            "Basic templates",
            "Community support",
        ],
        "limits": PlanLimits(
            generations_per_month=10,
            variations_per_generation=2,
            export_formats=["pptx"],
            custom_templates=False,
            api_access=False,
            team_members=1,
            priority_support=False,
        ),
    },
    PlanType.PRO: {
        "name": "Pro",
        "price_monthly": 2900,  # $29.00 in cents
        "price_yearly": 29000,  # $290.00 in cents ($24.17/mo)
        "stripe_price_id_monthly": "price_pro_monthly",  # Replace with actual Stripe price ID
        "stripe_price_id_yearly": "price_pro_yearly",
        "features": [
            "200 generations per month",
            "10 variations per generation",
            "PPTX, PDF, PNG export",
            "All templates",
            "Limited API access",
            "Email support",
        ],
        "limits": PlanLimits(
            generations_per_month=200,
            variations_per_generation=10,
            export_formats=["pptx", "pdf", "png", "svg"],
            custom_templates=True,
            api_access=True,
            team_members=1,
            priority_support=False,
        ),
    },
    PlanType.ENTERPRISE: {
        "name": "Enterprise",
        "price_monthly": None,  # Custom pricing
        "price_yearly": None,
        "stripe_price_id_monthly": None,
        "stripe_price_id_yearly": None,
        "features": [
            "Unlimited generations",
            "Unlimited variations",
            "All export formats",
            "Custom templates",
            "Full API access",
            "Unlimited team members",
            "Custom branding",
            "Dedicated support",
            "SSO/SAML",
        ],
        "limits": PlanLimits(
            generations_per_month=999999,
            variations_per_generation=999,
            export_formats=["pptx", "pdf", "png", "svg", "json"],
            custom_templates=True,
            api_access=True,
            team_members=999,
            priority_support=True,
        ),
    },
}


def get_plan(plan_type: PlanType) -> dict:
    """Get plan configuration.

    Args:
        plan_type: Plan type enum.

    Returns:
        Plan configuration dict.
    """
    return PLANS.get(plan_type, PLANS[PlanType.FREE])


def get_plan_limits(plan_type: PlanType) -> PlanLimits:
    """Get plan limits.

    Args:
        plan_type: Plan type enum.

    Returns:
        PlanLimits namedtuple.
    """
    plan = get_plan(plan_type)
    return plan["limits"]


def get_stripe_price_id(plan_type: PlanType, billing_period: str = "monthly") -> str | None:
    """Get Stripe price ID for a plan.

    Args:
        plan_type: Plan type.
        billing_period: 'monthly' or 'yearly'.

    Returns:
        Stripe price ID or None.
    """
    plan = get_plan(plan_type)
    key = f"stripe_price_id_{billing_period}"
    return plan.get(key)


def can_export_format(plan_type: PlanType, format: str) -> bool:
    """Check if plan allows a specific export format.

    Args:
        plan_type: Plan type.
        format: Export format (pptx, pdf, png, svg).

    Returns:
        True if allowed.
    """
    limits = get_plan_limits(plan_type)
    return format.lower() in limits.export_formats


def get_variation_limit(plan_type: PlanType) -> int:
    """Get variation limit for a plan.

    Args:
        plan_type: Plan type.

    Returns:
        Maximum variations per generation.
    """
    limits = get_plan_limits(plan_type)
    return limits.variations_per_generation
