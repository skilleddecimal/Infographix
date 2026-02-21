"""Enterprise webhook system for event notifications."""

from datetime import datetime
from enum import Enum
from typing import Any, Callable
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import asyncio

import httpx


class WebhookEvent(str, Enum):
    """Types of webhook events."""

    # Generation events
    GENERATION_STARTED = "generation.started"
    GENERATION_COMPLETED = "generation.completed"
    GENERATION_FAILED = "generation.failed"

    # Organization events
    MEMBER_ADDED = "organization.member_added"
    MEMBER_REMOVED = "organization.member_removed"
    INVITATION_ACCEPTED = "organization.invitation_accepted"

    # Brand compliance events
    COMPLIANCE_VIOLATION = "brand.compliance_violation"
    COMPLIANCE_CHECK_PASSED = "brand.compliance_check_passed"

    # User events
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"

    # Billing events
    SUBSCRIPTION_CREATED = "billing.subscription_created"
    SUBSCRIPTION_CANCELLED = "billing.subscription_cancelled"
    USAGE_LIMIT_REACHED = "billing.usage_limit_reached"
    USAGE_LIMIT_WARNING = "billing.usage_limit_warning"


@dataclass
class WebhookPayload:
    """Webhook payload structure."""

    event: WebhookEvent
    data: dict
    organization_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    webhook_id: str = ""

    def __post_init__(self):
        if not self.webhook_id:
            import secrets
            self.webhook_id = secrets.token_hex(16)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.webhook_id,
            "event": self.event.value,
            "data": self.data,
            "organization_id": self.organization_id,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class WebhookEndpoint:
    """Configuration for a webhook endpoint."""

    id: str
    url: str
    secret: str
    events: list[WebhookEvent]
    organization_id: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    failure_count: int = 0
    last_failure: datetime | None = None
    last_success: datetime | None = None


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""

    id: str
    endpoint_id: str
    payload: WebhookPayload
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None
    delivered_at: datetime = field(default_factory=datetime.utcnow)
    success: bool = False
    retry_count: int = 0


class WebhookManager:
    """
    Enterprise webhook management system.

    Handles registration, delivery, and retry of webhook events.
    Supports HMAC signature verification for security.
    """

    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 900]  # 1 min, 5 min, 15 min

    def __init__(self, db=None):
        self.db = db
        self._endpoints: dict[str, WebhookEndpoint] = {}
        self._deliveries: list[WebhookDelivery] = []
        self._handlers: dict[WebhookEvent, list[Callable]] = {}

    def register_endpoint(
        self,
        url: str,
        secret: str,
        events: list[WebhookEvent],
        organization_id: str | None = None,
    ) -> WebhookEndpoint:
        """
        Register a new webhook endpoint.

        Args:
            url: The URL to send webhook events to
            secret: Secret key for HMAC signing
            events: List of events to subscribe to
            organization_id: Optional org scope

        Returns:
            The created webhook endpoint
        """
        import secrets as secrets_module

        endpoint_id = secrets_module.token_hex(16)

        endpoint = WebhookEndpoint(
            id=endpoint_id,
            url=url,
            secret=secret,
            events=events,
            organization_id=organization_id,
        )

        self._endpoints[endpoint_id] = endpoint

        # Store to database if available
        if self.db:
            self._store_endpoint_to_db(endpoint)

        return endpoint

    def _store_endpoint_to_db(self, endpoint: WebhookEndpoint) -> None:
        """Store endpoint to database."""
        from backend.db.models import WebhookEndpoint as WebhookEndpointModel

        db_endpoint = WebhookEndpointModel(
            id=endpoint.id,
            url=endpoint.url,
            secret_hash=self._hash_secret(endpoint.secret),
            events=[e.value for e in endpoint.events],
            organization_id=endpoint.organization_id,
            is_active=endpoint.is_active,
        )
        self.db.add(db_endpoint)

    def _hash_secret(self, secret: str) -> str:
        """Hash the webhook secret for storage."""
        return hashlib.sha256(secret.encode()).hexdigest()

    def unregister_endpoint(self, endpoint_id: str) -> bool:
        """Unregister a webhook endpoint."""
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            return True

        if self.db:
            from backend.db.models import WebhookEndpoint as WebhookEndpointModel
            endpoint = self.db.query(WebhookEndpointModel).filter_by(id=endpoint_id).first()
            if endpoint:
                self.db.delete(endpoint)
                return True

        return False

    def get_endpoints(
        self,
        organization_id: str | None = None,
        event: WebhookEvent | None = None,
    ) -> list[WebhookEndpoint]:
        """Get webhook endpoints, optionally filtered."""
        endpoints = list(self._endpoints.values())

        if organization_id:
            endpoints = [e for e in endpoints if e.organization_id == organization_id]

        if event:
            endpoints = [e for e in endpoints if event in e.events]

        return [e for e in endpoints if e.is_active]

    def sign_payload(self, payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for payload.

        Args:
            payload: JSON payload string
            secret: Webhook secret

        Returns:
            Hex-encoded signature
        """
        signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        )
        return signature.hexdigest()

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: The payload that was signed
            signature: The signature to verify
            secret: The secret key

        Returns:
            True if signature is valid
        """
        expected = self.sign_payload(payload, secret)
        return hmac.compare_digest(expected, signature)

    async def emit(
        self,
        event: WebhookEvent,
        data: dict,
        organization_id: str | None = None,
    ) -> list[WebhookDelivery]:
        """
        Emit a webhook event to all subscribed endpoints.

        Args:
            event: The type of event
            data: Event data payload
            organization_id: Organization context

        Returns:
            List of delivery results
        """
        payload = WebhookPayload(
            event=event,
            data=data,
            organization_id=organization_id,
        )

        # Get matching endpoints
        endpoints = self.get_endpoints(organization_id=organization_id, event=event)

        # Deliver to all endpoints concurrently
        deliveries = await asyncio.gather(
            *[self._deliver(endpoint, payload) for endpoint in endpoints],
            return_exceptions=True,
        )

        results = []
        for delivery in deliveries:
            if isinstance(delivery, WebhookDelivery):
                results.append(delivery)
                self._deliveries.append(delivery)

        # Call local handlers
        if event in self._handlers:
            for handler in self._handlers[event]:
                try:
                    result = handler(payload)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    pass  # Log error but don't fail

        return results

    async def _deliver(
        self,
        endpoint: WebhookEndpoint,
        payload: WebhookPayload,
        retry_count: int = 0,
    ) -> WebhookDelivery:
        """
        Deliver webhook to a single endpoint.

        Args:
            endpoint: Target endpoint
            payload: Payload to deliver
            retry_count: Current retry attempt

        Returns:
            Delivery record
        """
        import secrets

        delivery_id = secrets.token_hex(16)
        payload_json = payload.to_json()
        signature = self.sign_payload(payload_json, endpoint.secret)

        delivery = WebhookDelivery(
            id=delivery_id,
            endpoint_id=endpoint.id,
            payload=payload,
            retry_count=retry_count,
        )

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-ID": payload.webhook_id,
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": payload.event.value,
            "X-Webhook-Timestamp": payload.timestamp.isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    endpoint.url,
                    content=payload_json,
                    headers=headers,
                )

            delivery.status_code = response.status_code
            delivery.response_body = response.text[:1000]  # Limit response size
            delivery.success = 200 <= response.status_code < 300

            if delivery.success:
                endpoint.last_success = datetime.utcnow()
                endpoint.failure_count = 0
            else:
                endpoint.last_failure = datetime.utcnow()
                endpoint.failure_count += 1

        except Exception as e:
            delivery.error = str(e)
            delivery.success = False
            endpoint.last_failure = datetime.utcnow()
            endpoint.failure_count += 1

        # Schedule retry if failed
        if not delivery.success and retry_count < self.MAX_RETRIES:
            delay = self.RETRY_DELAYS[retry_count]
            asyncio.create_task(self._retry_delivery(endpoint, payload, retry_count + 1, delay))

        return delivery

    async def _retry_delivery(
        self,
        endpoint: WebhookEndpoint,
        payload: WebhookPayload,
        retry_count: int,
        delay: int,
    ) -> None:
        """Schedule a retry delivery after delay."""
        await asyncio.sleep(delay)
        await self._deliver(endpoint, payload, retry_count)

    def on_event(self, event: WebhookEvent) -> Callable:
        """
        Decorator to register a local event handler.

        Usage:
            @webhook_manager.on_event(WebhookEvent.GENERATION_COMPLETED)
            async def handle_generation(payload):
                print(f"Generation completed: {payload.data}")
        """
        def decorator(func: Callable) -> Callable:
            if event not in self._handlers:
                self._handlers[event] = []
            self._handlers[event].append(func)
            return func
        return decorator

    def get_deliveries(
        self,
        endpoint_id: str | None = None,
        event: WebhookEvent | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        """Get webhook delivery history."""
        deliveries = self._deliveries.copy()

        if endpoint_id:
            deliveries = [d for d in deliveries if d.endpoint_id == endpoint_id]

        if event:
            deliveries = [d for d in deliveries if d.payload.event == event]

        if success is not None:
            deliveries = [d for d in deliveries if d.success == success]

        # Sort by delivery time, most recent first
        deliveries.sort(key=lambda d: d.delivered_at, reverse=True)

        return deliveries[:limit]

    def get_endpoint_stats(self, endpoint_id: str) -> dict:
        """Get statistics for a webhook endpoint."""
        endpoint = self._endpoints.get(endpoint_id)
        if not endpoint:
            return {}

        deliveries = [d for d in self._deliveries if d.endpoint_id == endpoint_id]
        successful = [d for d in deliveries if d.success]
        failed = [d for d in deliveries if not d.success]

        return {
            "endpoint_id": endpoint_id,
            "url": endpoint.url,
            "is_active": endpoint.is_active,
            "total_deliveries": len(deliveries),
            "successful_deliveries": len(successful),
            "failed_deliveries": len(failed),
            "success_rate": len(successful) / len(deliveries) if deliveries else 0,
            "failure_count": endpoint.failure_count,
            "last_success": endpoint.last_success.isoformat() if endpoint.last_success else None,
            "last_failure": endpoint.last_failure.isoformat() if endpoint.last_failure else None,
            "events": [e.value for e in endpoint.events],
        }


# Global instance for convenience
_webhook_manager: WebhookManager | None = None


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager instance."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


def emit_event(
    event: WebhookEvent,
    data: dict,
    organization_id: str | None = None,
) -> None:
    """
    Convenience function to emit a webhook event.

    This queues the event for async delivery.
    """
    manager = get_webhook_manager()
    asyncio.create_task(manager.emit(event, data, organization_id))
