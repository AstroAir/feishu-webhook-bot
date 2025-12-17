"""Webhook trigger for executing tasks via HTTP endpoints."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger

if TYPE_CHECKING:
    from .manager import TaskManager

logger = get_logger("task.webhook_trigger")


@dataclass
class WebhookTriggerConfig:
    """Configuration for a webhook trigger."""

    task_name: str
    secret: str | None = None
    allowed_methods: list[str] = field(default_factory=lambda: ["POST"])
    rate_limit: int = 60  # requests per minute
    enabled: bool = True
    require_auth: bool = False
    description: str | None = None


@dataclass
class WebhookTriggerResult:
    """Result of a webhook trigger execution."""

    success: bool
    task_name: str
    message: str
    execution_id: str | None = None
    task_result: dict[str, Any] | None = None
    error: str | None = None


class WebhookTriggerManager:
    """Manages webhook triggers for task execution.

    Provides HTTP endpoint handling for triggering tasks via webhooks with:
    - Secret-based authentication
    - Rate limiting
    - Request validation
    - Async execution support
    """

    def __init__(self, task_manager: TaskManager):
        """Initialize webhook trigger manager.

        Args:
            task_manager: TaskManager instance for executing tasks
        """
        self.task_manager = task_manager
        self._triggers: dict[str, WebhookTriggerConfig] = {}
        self._rate_limits: dict[str, list[float]] = {}  # trigger_id -> timestamps
        self._execution_tokens: dict[str, str] = {}  # token -> task_name

    def register_trigger(
        self,
        trigger_id: str,
        task_name: str,
        secret: str | None = None,
        allowed_methods: list[str] | None = None,
        rate_limit: int = 60,
        require_auth: bool = False,
        description: str | None = None,
    ) -> WebhookTriggerConfig:
        """Register a webhook trigger for a task.

        Args:
            trigger_id: Unique identifier for the trigger (used in URL path)
            task_name: Name of the task to trigger
            secret: Optional secret for HMAC signature verification
            allowed_methods: HTTP methods allowed (default: POST)
            rate_limit: Maximum requests per minute
            require_auth: Whether authentication is required
            description: Optional description

        Returns:
            The created trigger configuration
        """
        if task_name not in self.task_manager._task_instances:
            # Check if task exists in config
            task = self.task_manager.config.get_task(task_name)
            if not task:
                raise ValueError(f"Task not found: {task_name}")

        config = WebhookTriggerConfig(
            task_name=task_name,
            secret=secret,
            allowed_methods=allowed_methods or ["POST"],
            rate_limit=rate_limit,
            enabled=True,
            require_auth=require_auth,
            description=description,
        )

        self._triggers[trigger_id] = config
        logger.info(f"Registered webhook trigger '{trigger_id}' for task '{task_name}'")
        return config

    def unregister_trigger(self, trigger_id: str) -> bool:
        """Unregister a webhook trigger.

        Args:
            trigger_id: ID of the trigger to remove

        Returns:
            True if removed, False if not found
        """
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            if trigger_id in self._rate_limits:
                del self._rate_limits[trigger_id]
            logger.info(f"Unregistered webhook trigger: {trigger_id}")
            return True
        return False

    def get_trigger(self, trigger_id: str) -> WebhookTriggerConfig | None:
        """Get a trigger configuration by ID.

        Args:
            trigger_id: ID of the trigger

        Returns:
            Trigger configuration or None
        """
        return self._triggers.get(trigger_id)

    def list_triggers(self) -> dict[str, WebhookTriggerConfig]:
        """List all registered triggers.

        Returns:
            Dictionary of trigger ID to configuration
        """
        return dict(self._triggers)

    def enable_trigger(self, trigger_id: str) -> bool:
        """Enable a trigger.

        Args:
            trigger_id: ID of the trigger

        Returns:
            True if enabled, False if not found
        """
        trigger = self._triggers.get(trigger_id)
        if trigger:
            trigger.enabled = True
            return True
        return False

    def disable_trigger(self, trigger_id: str) -> bool:
        """Disable a trigger.

        Args:
            trigger_id: ID of the trigger

        Returns:
            True if disabled, False if not found
        """
        trigger = self._triggers.get(trigger_id)
        if trigger:
            trigger.enabled = False
            return True
        return False

    def verify_signature(
        self,
        trigger_id: str,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify HMAC signature for a webhook request.

        Args:
            trigger_id: ID of the trigger
            payload: Request body bytes
            signature: Signature from request header

        Returns:
            True if signature is valid
        """
        trigger = self._triggers.get(trigger_id)
        if not trigger or not trigger.secret:
            return True  # No secret configured, skip verification

        expected = hmac.new(
            trigger.secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # Support both raw and prefixed signatures
        if signature.startswith("sha256="):
            signature = signature[7:]

        return hmac.compare_digest(expected, signature)

    def check_rate_limit(self, trigger_id: str) -> bool:
        """Check if request is within rate limit.

        Args:
            trigger_id: ID of the trigger

        Returns:
            True if within limit, False if exceeded
        """
        trigger = self._triggers.get(trigger_id)
        if not trigger:
            return False

        now = time.time()
        window_start = now - 60  # 1 minute window

        # Get timestamps for this trigger
        timestamps = self._rate_limits.get(trigger_id, [])

        # Remove old timestamps
        timestamps = [ts for ts in timestamps if ts > window_start]

        # Check limit
        if len(timestamps) >= trigger.rate_limit:
            return False

        # Record this request
        timestamps.append(now)
        self._rate_limits[trigger_id] = timestamps
        return True

    def handle_webhook(
        self,
        trigger_id: str,
        method: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        async_execution: bool = False,
    ) -> WebhookTriggerResult:
        """Handle an incoming webhook request.

        Args:
            trigger_id: ID of the trigger
            method: HTTP method
            payload: Parsed request body (JSON)
            headers: Request headers
            body: Raw request body for signature verification
            async_execution: If True, execute task asynchronously

        Returns:
            WebhookTriggerResult with execution status
        """
        headers = headers or {}

        # Get trigger config
        trigger = self._triggers.get(trigger_id)
        if not trigger:
            return WebhookTriggerResult(
                success=False,
                task_name="",
                message="Trigger not found",
                error=f"Unknown trigger: {trigger_id}",
            )

        # Check if enabled
        if not trigger.enabled:
            return WebhookTriggerResult(
                success=False,
                task_name=trigger.task_name,
                message="Trigger is disabled",
                error="Trigger is currently disabled",
            )

        # Check HTTP method
        if method.upper() not in trigger.allowed_methods:
            return WebhookTriggerResult(
                success=False,
                task_name=trigger.task_name,
                message="Method not allowed",
                error=f"Method {method} not in {trigger.allowed_methods}",
            )

        # Check rate limit
        if not self.check_rate_limit(trigger_id):
            return WebhookTriggerResult(
                success=False,
                task_name=trigger.task_name,
                message="Rate limit exceeded",
                error="Too many requests, please try again later",
            )

        # Verify signature if secret is configured
        if trigger.secret and body:
            signature = headers.get("X-Signature-256") or headers.get("X-Hub-Signature-256", "")
            if not self.verify_signature(trigger_id, body, signature):
                return WebhookTriggerResult(
                    success=False,
                    task_name=trigger.task_name,
                    message="Invalid signature",
                    error="Signature verification failed",
                )

        # Build context from payload
        context = payload or {}
        context["_webhook_trigger"] = {
            "trigger_id": trigger_id,
            "method": method,
            "timestamp": time.time(),
        }

        # Execute task
        execution_id = secrets.token_hex(8)

        if async_execution:
            # Execute asynchronously
            import threading

            def run_async() -> None:
                try:
                    self.task_manager.run_task_with_params(
                        trigger.task_name,
                        params=context,
                        force=True,
                    )
                except Exception as e:
                    logger.error(f"Async task execution failed: {e}")

            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()

            return WebhookTriggerResult(
                success=True,
                task_name=trigger.task_name,
                message="Task execution started",
                execution_id=execution_id,
            )
        else:
            # Execute synchronously
            try:
                result = self.task_manager.run_task_with_params(
                    trigger.task_name,
                    params=context,
                    force=True,
                )

                return WebhookTriggerResult(
                    success=result.get("success", False),
                    task_name=trigger.task_name,
                    message="Task executed" if result.get("success") else "Task failed",
                    execution_id=execution_id,
                    task_result=result,
                    error=result.get("error"),
                )
            except Exception as e:
                logger.error(f"Task execution failed: {e}", exc_info=True)
                return WebhookTriggerResult(
                    success=False,
                    task_name=trigger.task_name,
                    message="Task execution failed",
                    execution_id=execution_id,
                    error=str(e),
                )

    def generate_trigger_url(
        self,
        trigger_id: str,
        base_url: str = "http://localhost:8000",
    ) -> str:
        """Generate the webhook URL for a trigger.

        Args:
            trigger_id: ID of the trigger
            base_url: Base URL of the server

        Returns:
            Full webhook URL
        """
        return f"{base_url.rstrip('/')}/api/tasks/webhook/{trigger_id}"

    def generate_secret(self) -> str:
        """Generate a secure random secret for webhook signing.

        Returns:
            Random secret string
        """
        return secrets.token_hex(32)


def create_webhook_routes(trigger_manager: WebhookTriggerManager) -> Any:
    """Create FastAPI routes for webhook triggers.

    Args:
        trigger_manager: WebhookTriggerManager instance

    Returns:
        FastAPI APIRouter with webhook endpoints
    """
    try:
        from fastapi import APIRouter, Header, Request
        from fastapi.responses import JSONResponse
    except ImportError:
        logger.warning("FastAPI not installed, webhook routes not available")
        return None

    router = APIRouter(prefix="/api/tasks/webhook", tags=["task-webhooks"])

    @router.post("/{trigger_id}")
    @router.get("/{trigger_id}")
    @router.put("/{trigger_id}")
    async def handle_webhook(
        trigger_id: str,
        request: Request,
        x_signature_256: str | None = Header(None),
        x_async: bool = Header(False, alias="X-Async"),
    ) -> JSONResponse:
        """Handle incoming webhook request."""
        # Get raw body for signature verification
        body = await request.body()

        # Parse JSON payload if present
        payload = None
        if body:
            import contextlib

            with contextlib.suppress(Exception):
                payload = await request.json()

        # Get headers
        headers = dict(request.headers)
        if x_signature_256:
            headers["X-Signature-256"] = x_signature_256

        # Handle webhook
        result = trigger_manager.handle_webhook(
            trigger_id=trigger_id,
            method=request.method,
            payload=payload,
            headers=headers,
            body=body,
            async_execution=x_async,
        )

        status_code = 200 if result.success else 400
        if "not found" in result.message.lower():
            status_code = 404
        elif "rate limit" in result.message.lower():
            status_code = 429
        elif "not allowed" in result.message.lower():
            status_code = 405
        elif "signature" in result.message.lower():
            status_code = 401

        return JSONResponse(
            status_code=status_code,
            content={
                "success": result.success,
                "task_name": result.task_name,
                "message": result.message,
                "execution_id": result.execution_id,
                "error": result.error,
            },
        )

    @router.get("/")
    async def list_triggers() -> JSONResponse:
        """List all registered webhook triggers."""
        triggers = trigger_manager.list_triggers()
        return JSONResponse(
            content={
                "triggers": {
                    tid: {
                        "task_name": cfg.task_name,
                        "enabled": cfg.enabled,
                        "allowed_methods": cfg.allowed_methods,
                        "rate_limit": cfg.rate_limit,
                        "require_auth": cfg.require_auth,
                        "description": cfg.description,
                    }
                    for tid, cfg in triggers.items()
                }
            }
        )

    return router
