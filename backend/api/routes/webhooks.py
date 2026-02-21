"""Webhook routes for Enterprise."""

import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import (
    User,
    MemberRole,
    WebhookEndpoint as WebhookEndpointModel,
    WebhookDelivery as WebhookDeliveryModel,
)
from backend.api.dependencies import CurrentUser
from backend.api.routes.organizations import require_org_role
from backend.enterprise.webhooks import WebhookEvent


router = APIRouter()


# Valid webhook events
VALID_EVENTS = [e.value for e in WebhookEvent]


class CreateWebhookRequest(BaseModel):
    """Create webhook endpoint request."""
    url: str = Field(..., min_length=10, max_length=500)
    events: list[str] = Field(..., min_items=1)
    description: str | None = None

    def validate_events(self) -> list[str]:
        """Validate that all events are valid."""
        invalid = [e for e in self.events if e not in VALID_EVENTS]
        if invalid:
            raise ValueError(f"Invalid events: {invalid}")
        return self.events


class UpdateWebhookRequest(BaseModel):
    """Update webhook endpoint request."""
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None
    description: str | None = None


class WebhookEndpointResponse(BaseModel):
    """Webhook endpoint response."""
    id: str
    organization_id: str | None
    url: str
    events: list[str]
    is_active: bool
    failure_count: int
    last_success_at: str | None
    last_failure_at: str | None
    created_at: str
    updated_at: str


class WebhookSecretResponse(BaseModel):
    """Response when creating webhook with secret."""
    endpoint: WebhookEndpointResponse
    secret: str  # Only returned on creation


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery response."""
    id: str
    endpoint_id: str
    event_type: str
    status_code: int | None
    success: bool
    error: str | None
    retry_count: int
    created_at: str
    delivered_at: str | None


def endpoint_to_response(endpoint: WebhookEndpointModel) -> WebhookEndpointResponse:
    """Convert WebhookEndpoint model to response."""
    return WebhookEndpointResponse(
        id=endpoint.id,
        organization_id=endpoint.organization_id,
        url=endpoint.url,
        events=endpoint.events or [],
        is_active=endpoint.is_active,
        failure_count=endpoint.failure_count,
        last_success_at=endpoint.last_success_at.isoformat() if endpoint.last_success_at else None,
        last_failure_at=endpoint.last_failure_at.isoformat() if endpoint.last_failure_at else None,
        created_at=endpoint.created_at.isoformat(),
        updated_at=endpoint.updated_at.isoformat(),
    )


def delivery_to_response(delivery: WebhookDeliveryModel) -> WebhookDeliveryResponse:
    """Convert WebhookDelivery model to response."""
    return WebhookDeliveryResponse(
        id=delivery.id,
        endpoint_id=delivery.endpoint_id,
        event_type=delivery.event_type,
        status_code=delivery.status_code,
        success=delivery.success,
        error=delivery.error,
        retry_count=delivery.retry_count,
        created_at=delivery.created_at.isoformat(),
        delivered_at=delivery.delivered_at.isoformat() if delivery.delivered_at else None,
    )


@router.get("/{org_id}/webhooks", response_model=list[WebhookEndpointResponse])
async def list_webhooks(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """List webhook endpoints for an organization."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    endpoints = db.query(WebhookEndpointModel).filter(
        WebhookEndpointModel.organization_id == org_id
    ).order_by(WebhookEndpointModel.created_at.desc()).all()

    return [endpoint_to_response(e) for e in endpoints]


@router.get("/{org_id}/webhooks/{webhook_id}", response_model=WebhookEndpointResponse)
async def get_webhook(
    org_id: str,
    webhook_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get a specific webhook endpoint."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    endpoint = db.query(WebhookEndpointModel).filter(
        WebhookEndpointModel.id == webhook_id,
        WebhookEndpointModel.organization_id == org_id,
    ).first()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found",
        )

    return endpoint_to_response(endpoint)


@router.post("/{org_id}/webhooks", response_model=WebhookSecretResponse)
async def create_webhook(
    org_id: str,
    request: CreateWebhookRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Create a new webhook endpoint.

    Returns the endpoint along with the signing secret.
    Store the secret securely - it will not be shown again.
    """
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    # Validate events
    try:
        request.validate_events()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Generate signing secret
    secret = f"whsec_{secrets.token_hex(32)}"
    secret_hash = __import__("hashlib").sha256(secret.encode()).hexdigest()

    endpoint = WebhookEndpointModel(
        organization_id=org_id,
        url=request.url,
        secret_hash=secret_hash,
        events=request.events,
    )

    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)

    return WebhookSecretResponse(
        endpoint=endpoint_to_response(endpoint),
        secret=secret,
    )


@router.patch("/{org_id}/webhooks/{webhook_id}", response_model=WebhookEndpointResponse)
async def update_webhook(
    org_id: str,
    webhook_id: str,
    request: UpdateWebhookRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Update a webhook endpoint."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    endpoint = db.query(WebhookEndpointModel).filter(
        WebhookEndpointModel.id == webhook_id,
        WebhookEndpointModel.organization_id == org_id,
    ).first()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found",
        )

    # Validate events if provided
    if request.events:
        invalid = [e for e in request.events if e not in VALID_EVENTS]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid events: {invalid}",
            )
        endpoint.events = request.events

    if request.url is not None:
        endpoint.url = request.url
    if request.is_active is not None:
        endpoint.is_active = request.is_active

    db.commit()
    db.refresh(endpoint)

    return endpoint_to_response(endpoint)


@router.delete("/{org_id}/webhooks/{webhook_id}")
async def delete_webhook(
    org_id: str,
    webhook_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Delete a webhook endpoint."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    endpoint = db.query(WebhookEndpointModel).filter(
        WebhookEndpointModel.id == webhook_id,
        WebhookEndpointModel.organization_id == org_id,
    ).first()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found",
        )

    db.delete(endpoint)
    db.commit()

    return {"status": "webhook_deleted"}


@router.post("/{org_id}/webhooks/{webhook_id}/rotate-secret", response_model=WebhookSecretResponse)
async def rotate_webhook_secret(
    org_id: str,
    webhook_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Rotate the signing secret for a webhook endpoint.

    Returns the new secret. Store it securely - it will not be shown again.
    """
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    endpoint = db.query(WebhookEndpointModel).filter(
        WebhookEndpointModel.id == webhook_id,
        WebhookEndpointModel.organization_id == org_id,
    ).first()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found",
        )

    # Generate new secret
    secret = f"whsec_{secrets.token_hex(32)}"
    endpoint.secret_hash = __import__("hashlib").sha256(secret.encode()).hexdigest()

    db.commit()
    db.refresh(endpoint)

    return WebhookSecretResponse(
        endpoint=endpoint_to_response(endpoint),
        secret=secret,
    )


@router.get("/{org_id}/webhooks/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    org_id: str,
    webhook_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    success: bool | None = None,
    limit: int = Query(50, ge=1, le=100),
):
    """List recent deliveries for a webhook endpoint."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    # Verify endpoint exists and belongs to org
    endpoint = db.query(WebhookEndpointModel).filter(
        WebhookEndpointModel.id == webhook_id,
        WebhookEndpointModel.organization_id == org_id,
    ).first()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found",
        )

    query = db.query(WebhookDeliveryModel).filter(
        WebhookDeliveryModel.endpoint_id == webhook_id
    )

    if success is not None:
        query = query.filter(WebhookDeliveryModel.success == success)

    deliveries = query.order_by(
        WebhookDeliveryModel.created_at.desc()
    ).limit(limit).all()

    return [delivery_to_response(d) for d in deliveries]


@router.post("/{org_id}/webhooks/{webhook_id}/test")
async def test_webhook(
    org_id: str,
    webhook_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Send a test event to a webhook endpoint.

    Sends a 'test.ping' event to verify the endpoint is working.
    """
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    endpoint = db.query(WebhookEndpointModel).filter(
        WebhookEndpointModel.id == webhook_id,
        WebhookEndpointModel.organization_id == org_id,
    ).first()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found",
        )

    # Import httpx for making the test request
    import httpx
    import hashlib
    import hmac
    import json

    payload = {
        "id": secrets.token_hex(16),
        "event": "test.ping",
        "data": {
            "message": "This is a test webhook event",
            "timestamp": datetime.utcnow().isoformat(),
        },
        "organization_id": org_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    payload_json = json.dumps(payload)

    # We don't have the actual secret, just the hash, so we can't sign properly
    # In a real implementation, you'd store the secret encrypted
    # For now, we'll just test connectivity

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                endpoint.url,
                content=payload_json,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Event": "test.ping",
                    "X-Webhook-ID": payload["id"],
                },
            )

        return {
            "status": "delivered",
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response_time_ms": int(response.elapsed.total_seconds() * 1000),
        }

    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "success": False,
            "error": "Request timed out",
        }
    except httpx.RequestError as e:
        return {
            "status": "error",
            "success": False,
            "error": str(e),
        }


@router.get("/webhook-events")
async def list_webhook_events(
    current_user: CurrentUser,
):
    """List available webhook event types."""
    events = []
    for event in WebhookEvent:
        category, action = event.value.split(".", 1)
        events.append({
            "event": event.value,
            "category": category,
            "action": action,
        })

    return {"events": events}
