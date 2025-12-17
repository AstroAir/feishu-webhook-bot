"""Enhanced trigger system for automation engine.

This module provides various trigger types that can initiate automation workflows.
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger

if TYPE_CHECKING:
    from ..scheduler import TaskScheduler

logger = get_logger("automation.triggers")


class TriggerType(str, Enum):
    """Supported trigger types."""

    SCHEDULE = "schedule"
    EVENT = "event"
    WEBHOOK = "webhook"
    FILE_CHANGE = "file_change"
    MANUAL = "manual"
    CHAIN = "chain"
    CRON = "cron"
    INTERVAL = "interval"


@dataclass
class TriggerContext:
    """Context passed to rule execution when triggered."""

    trigger_type: TriggerType
    triggered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    trigger_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trigger_type": self.trigger_type.value,
            "triggered_at": self.triggered_at,
            "trigger_id": self.trigger_id,
            "payload": self.payload,
            "metadata": self.metadata,
        }


class BaseTrigger(ABC):
    """Base class for automation triggers."""

    trigger_type: TriggerType

    def __init__(
        self,
        rule_name: str,
        config: Mapping[str, Any],
        callback: Callable[[TriggerContext], None],
    ) -> None:
        self.rule_name = rule_name
        self.config = config
        self.callback = callback
        self.enabled = True
        self._last_triggered: datetime | None = None

    @abstractmethod
    def start(self) -> None:
        """Start the trigger (begin listening/scheduling)."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the trigger."""
        pass

    def trigger(self, context: TriggerContext | None = None) -> None:
        """Fire the trigger with the given context."""
        if not self.enabled:
            logger.debug("Trigger disabled for rule: %s", self.rule_name)
            return

        if context is None:
            context = TriggerContext(
                trigger_type=self.trigger_type,
                trigger_id=f"{self.rule_name}_{int(time.time())}",
            )

        self._last_triggered = datetime.now()
        logger.debug("Trigger fired for rule: %s", self.rule_name)

        try:
            self.callback(context)
        except Exception as e:
            logger.error(
                "Trigger callback failed for rule %s: %s",
                self.rule_name,
                e,
                exc_info=True,
            )

    @property
    def last_triggered(self) -> datetime | None:
        """Get the last trigger time."""
        return self._last_triggered


class ScheduleTrigger(BaseTrigger):
    """Schedule-based trigger using APScheduler."""

    trigger_type = TriggerType.SCHEDULE

    def __init__(
        self,
        rule_name: str,
        config: Mapping[str, Any],
        callback: Callable[[TriggerContext], None],
        scheduler: TaskScheduler | None = None,
    ) -> None:
        super().__init__(rule_name, config, callback)
        self.scheduler = scheduler
        self._job_id: str | None = None

    def start(self) -> None:
        """Register the schedule with the scheduler."""
        if not self.scheduler:
            logger.warning("Scheduler not available for rule: %s", self.rule_name)
            return

        mode = self.config.get("mode", "interval")
        arguments = self.config.get("arguments", {})

        self._job_id = f"automation.{self.rule_name}"

        try:
            self._job_id = self.scheduler.add_job(
                self._on_schedule,
                trigger=mode,
                job_id=self._job_id,
                replace_existing=True,
                **arguments,
            )
            logger.info(
                "Registered schedule trigger '%s' with mode %s",
                self.rule_name,
                mode,
            )
        except Exception as e:
            logger.error(
                "Failed to register schedule for rule %s: %s",
                self.rule_name,
                e,
                exc_info=True,
            )

    def stop(self) -> None:
        """Remove the scheduled job."""
        if self._job_id and self.scheduler:
            try:
                self.scheduler.remove_job(self._job_id)
                logger.debug("Removed schedule job: %s", self._job_id)
            except Exception as e:
                logger.debug("Failed to remove job %s: %s", self._job_id, e)
            finally:
                self._job_id = None

    def _on_schedule(self) -> None:
        """Called when the schedule fires."""
        context = TriggerContext(
            trigger_type=self.trigger_type,
            trigger_id=f"{self.rule_name}_{int(time.time())}",
            metadata={
                "mode": self.config.get("mode"),
                "arguments": self.config.get("arguments"),
            },
        )
        self.trigger(context)

    def get_next_run_time(self) -> datetime | None:
        """Get the next scheduled run time."""
        if self._job_id and self.scheduler:
            job = self.scheduler.get_job(self._job_id)
            if job:
                return job.next_run_time
        return None


class EventTrigger(BaseTrigger):
    """Event-based trigger that responds to incoming events."""

    trigger_type = TriggerType.EVENT

    def __init__(
        self,
        rule_name: str,
        config: Mapping[str, Any],
        callback: Callable[[TriggerContext], None],
    ) -> None:
        super().__init__(rule_name, config, callback)
        self.event_type = config.get("event_type")
        self.conditions = config.get("conditions", [])

    def start(self) -> None:
        """Event triggers are passive - they respond to events."""
        logger.debug(
            "Event trigger registered for rule: %s (type: %s)",
            self.rule_name,
            self.event_type,
        )

    def stop(self) -> None:
        """Event triggers don't need explicit stopping."""
        pass

    def matches(self, event_payload: Mapping[str, Any]) -> bool:
        """Check if the event matches this trigger's criteria.

        Args:
            event_payload: The incoming event payload

        Returns:
            True if the event matches all conditions
        """
        # Check event type if specified
        if self.event_type:
            event_type = self._extract(event_payload, "header.event_type")
            if event_type != self.event_type:
                return False

        # Check all conditions
        return all(self._check_condition(condition, event_payload) for condition in self.conditions)

    def handle_event(self, event_payload: Mapping[str, Any]) -> bool:
        """Handle an incoming event if it matches.

        Args:
            event_payload: The incoming event payload

        Returns:
            True if the event was handled
        """
        if not self.matches(event_payload):
            return False

        context = TriggerContext(
            trigger_type=self.trigger_type,
            trigger_id=f"{self.rule_name}_{int(time.time())}",
            payload=dict(event_payload),
            metadata={
                "event_type": self.event_type,
                "conditions_matched": len(self.conditions),
            },
        )
        self.trigger(context)
        return True

    def _extract(self, payload: Mapping[str, Any], path: str) -> Any:
        """Extract a value from the payload using dot notation."""
        current: Any = payload
        for part in path.split("."):
            if isinstance(current, Mapping):
                current = current.get(part)
            else:
                return None
        return current

    def _check_condition(self, condition: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
        """Check a single condition against the payload."""
        path = condition.get("path", "")
        value = self._extract(payload, path)

        # Check equals
        if "equals" in condition and value != condition["equals"]:
            return False

        # Check contains
        if "contains" in condition and (
            not isinstance(value, str) or condition["contains"] not in value
        ):
            return False

        # Check regex
        if "regex" in condition:
            if not isinstance(value, str):
                return False
            try:
                if not re.search(condition["regex"], value):
                    return False
            except re.error:
                return False

        # Check exists
        if "exists" in condition and (value is not None) != condition["exists"]:
            return False

        # Check greater_than
        if "greater_than" in condition:
            try:
                if float(value) <= float(condition["greater_than"]):
                    return False
            except (TypeError, ValueError):
                return False

        # Check less_than
        if "less_than" in condition:
            try:
                if float(value) >= float(condition["less_than"]):
                    return False
            except (TypeError, ValueError):
                return False

        # Check in_list
        return not ("in_list" in condition and value not in condition["in_list"])


class WebhookTrigger(BaseTrigger):
    """HTTP webhook trigger for external integrations."""

    trigger_type = TriggerType.WEBHOOK

    def __init__(
        self,
        rule_name: str,
        config: Mapping[str, Any],
        callback: Callable[[TriggerContext], None],
    ) -> None:
        super().__init__(rule_name, config, callback)
        self.path = config.get("path", f"/automation/{rule_name}")
        self.methods = config.get("methods", ["POST"])
        self.secret = config.get("secret")
        self.validate_payload = config.get("validate_payload", False)
        self.payload_schema = config.get("payload_schema", {})

    def start(self) -> None:
        """Register webhook endpoint."""
        logger.info(
            "Webhook trigger registered for rule: %s at path %s",
            self.rule_name,
            self.path,
        )

    def stop(self) -> None:
        """Unregister webhook endpoint."""
        logger.debug("Webhook trigger stopped for rule: %s", self.rule_name)

    def handle_request(
        self,
        method: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[bool, str]:
        """Handle an incoming webhook request.

        Args:
            method: HTTP method
            payload: Request payload
            headers: Request headers

        Returns:
            Tuple of (success, message)
        """
        # Check method
        if method.upper() not in [m.upper() for m in self.methods]:
            return False, f"Method {method} not allowed"

        # Validate signature if secret is set
        if self.secret:
            signature = headers.get("X-Signature") or headers.get("x-signature")
            if not self._validate_signature(payload, signature):
                return False, "Invalid signature"

        # Validate payload schema if enabled
        if self.validate_payload and self.payload_schema:
            valid, error = self._validate_payload(payload)
            if not valid:
                return False, f"Payload validation failed: {error}"

        # Trigger the rule
        context = TriggerContext(
            trigger_type=self.trigger_type,
            trigger_id=f"{self.rule_name}_{int(time.time())}",
            payload=payload,
            metadata={
                "method": method,
                "path": self.path,
                "headers": {k: v for k, v in headers.items() if not k.lower().startswith("x-")},
            },
        )
        self.trigger(context)
        return True, "OK"

    def _validate_signature(self, payload: dict[str, Any], signature: str | None) -> bool:
        """Validate webhook signature."""
        if not signature or not self.secret:
            return False

        import json

        payload_str = json.dumps(payload, sort_keys=True)
        expected = hashlib.sha256(f"{self.secret}{payload_str}".encode()).hexdigest()
        return signature == expected

    def _validate_payload(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate payload against schema (basic validation)."""
        for field_name, field_config in self.payload_schema.items():
            required = field_config.get("required", False)
            field_type = field_config.get("type", "string")

            if required and field_name not in payload:
                return False, f"Missing required field: {field_name}"

            if field_name in payload:
                value = payload[field_name]
                if field_type == "string" and not isinstance(value, str):
                    return False, f"Field {field_name} must be string"
                if field_type == "number" and not isinstance(value, (int, float)):
                    return False, f"Field {field_name} must be number"
                if field_type == "boolean" and not isinstance(value, bool):
                    return False, f"Field {field_name} must be boolean"
                if field_type == "array" and not isinstance(value, list):
                    return False, f"Field {field_name} must be array"
                if field_type == "object" and not isinstance(value, dict):
                    return False, f"Field {field_name} must be object"

        return True, None


class ManualTrigger(BaseTrigger):
    """Manual trigger that can be fired programmatically."""

    trigger_type = TriggerType.MANUAL

    def __init__(
        self,
        rule_name: str,
        config: Mapping[str, Any],
        callback: Callable[[TriggerContext], None],
    ) -> None:
        super().__init__(rule_name, config, callback)
        self.parameters = config.get("parameters", [])
        self.require_confirmation = config.get("require_confirmation", False)
        self.description = config.get("description", "")

    def start(self) -> None:
        """Manual triggers are always ready."""
        logger.debug("Manual trigger registered for rule: %s", self.rule_name)

    def stop(self) -> None:
        """Manual triggers don't need stopping."""
        pass

    def fire(
        self,
        params: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> tuple[bool, str]:
        """Fire the manual trigger.

        Args:
            params: Parameters to pass to the rule
            user_id: ID of user triggering the rule

        Returns:
            Tuple of (success, message)
        """
        # Validate required parameters
        params = params or {}
        for param_config in self.parameters:
            param_name = param_config.get("name")
            required = param_config.get("required", False)

            if required and param_name not in params:
                return False, f"Missing required parameter: {param_name}"

            # Type validation
            if param_name in params:
                param_type = param_config.get("type", "string")
                value = params[param_name]
                if not self._validate_param_type(value, param_type):
                    return False, f"Invalid type for parameter {param_name}"

        context = TriggerContext(
            trigger_type=self.trigger_type,
            trigger_id=f"{self.rule_name}_{int(time.time())}",
            payload=params,
            metadata={
                "user_id": user_id,
                "manual": True,
            },
        )
        self.trigger(context)
        return True, "OK"

    def _validate_param_type(self, value: Any, expected_type: str) -> bool:
        """Validate parameter type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True
        return isinstance(value, expected)

    def get_parameter_schema(self) -> list[dict[str, Any]]:
        """Get the parameter schema for UI rendering."""
        return self.parameters


class ChainTrigger(BaseTrigger):
    """Trigger that fires when another rule completes."""

    trigger_type = TriggerType.CHAIN

    def __init__(
        self,
        rule_name: str,
        config: Mapping[str, Any],
        callback: Callable[[TriggerContext], None],
    ) -> None:
        super().__init__(rule_name, config, callback)
        self.source_rules = config.get("source_rules", [])
        self.require_success = config.get("require_success", True)
        self.wait_all = config.get("wait_all", False)
        self._completed_rules: set[str] = set()

    def start(self) -> None:
        """Chain triggers are passive."""
        logger.debug(
            "Chain trigger registered for rule: %s (watching: %s)",
            self.rule_name,
            ", ".join(self.source_rules),
        )

    def stop(self) -> None:
        """Reset state."""
        self._completed_rules.clear()

    def on_rule_completed(
        self,
        source_rule: str,
        success: bool,
        result: dict[str, Any] | None = None,
    ) -> bool:
        """Called when a source rule completes.

        Args:
            source_rule: Name of the completed rule
            success: Whether the rule succeeded
            result: Rule execution result

        Returns:
            True if this trigger fired
        """
        if source_rule not in self.source_rules:
            return False

        if self.require_success and not success:
            logger.debug(
                "Chain trigger %s: source rule %s failed, not triggering",
                self.rule_name,
                source_rule,
            )
            return False

        if self.wait_all:
            self._completed_rules.add(source_rule)
            if self._completed_rules != set(self.source_rules):
                logger.debug(
                    "Chain trigger %s: waiting for more rules (%d/%d)",
                    self.rule_name,
                    len(self._completed_rules),
                    len(self.source_rules),
                )
                return False
            # Reset for next cycle
            self._completed_rules.clear()

        context = TriggerContext(
            trigger_type=self.trigger_type,
            trigger_id=f"{self.rule_name}_{int(time.time())}",
            payload=result or {},
            metadata={
                "source_rule": source_rule,
                "success": success,
                "wait_all": self.wait_all,
            },
        )
        self.trigger(context)
        return True


class TriggerRegistry:
    """Registry for managing automation triggers."""

    def __init__(self, scheduler: TaskScheduler | None = None) -> None:
        self.scheduler = scheduler
        self._triggers: dict[str, BaseTrigger] = {}
        self._event_triggers: list[EventTrigger] = []
        self._webhook_triggers: dict[str, WebhookTrigger] = {}
        self._chain_triggers: dict[str, list[ChainTrigger]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        rule_name: str,
        trigger_config: Mapping[str, Any],
        callback: Callable[[TriggerContext], None],
    ) -> BaseTrigger | None:
        """Register a trigger for a rule.

        Args:
            rule_name: Name of the automation rule
            trigger_config: Trigger configuration
            callback: Function to call when trigger fires

        Returns:
            The created trigger instance
        """
        trigger_type = trigger_config.get("type", "schedule")

        try:
            trigger_type_enum = TriggerType(trigger_type)
        except ValueError:
            logger.error("Unknown trigger type: %s", trigger_type)
            return None

        trigger: BaseTrigger | None = None

        if trigger_type_enum == TriggerType.SCHEDULE:
            schedule_config = trigger_config.get("schedule", {})
            trigger = ScheduleTrigger(rule_name, schedule_config, callback, self.scheduler)

        elif trigger_type_enum == TriggerType.EVENT:
            event_config = trigger_config.get("event", {})
            trigger = EventTrigger(rule_name, event_config, callback)
            with self._lock:
                self._event_triggers.append(trigger)

        elif trigger_type_enum == TriggerType.WEBHOOK:
            webhook_config = trigger_config.get("webhook", {})
            trigger = WebhookTrigger(rule_name, webhook_config, callback)
            with self._lock:
                self._webhook_triggers[trigger.path] = trigger

        elif trigger_type_enum == TriggerType.MANUAL:
            manual_config = trigger_config.get("manual", {})
            trigger = ManualTrigger(rule_name, manual_config, callback)

        elif trigger_type_enum == TriggerType.CHAIN:
            chain_config = trigger_config.get("chain", {})
            trigger = ChainTrigger(rule_name, chain_config, callback)
            with self._lock:
                for source_rule in chain_config.get("source_rules", []):
                    if source_rule not in self._chain_triggers:
                        self._chain_triggers[source_rule] = []
                    self._chain_triggers[source_rule].append(trigger)

        if trigger:
            with self._lock:
                self._triggers[rule_name] = trigger
            trigger.start()
            logger.info(
                "Registered %s trigger for rule: %s",
                trigger_type,
                rule_name,
            )

        return trigger

    def unregister(self, rule_name: str) -> bool:
        """Unregister a trigger.

        Args:
            rule_name: Name of the rule to unregister

        Returns:
            True if trigger was found and removed
        """
        with self._lock:
            trigger = self._triggers.pop(rule_name, None)
            if not trigger:
                return False

            trigger.stop()

            # Clean up from type-specific registries
            if isinstance(trigger, EventTrigger):
                self._event_triggers = [t for t in self._event_triggers if t.rule_name != rule_name]
            elif isinstance(trigger, WebhookTrigger):
                self._webhook_triggers = {
                    k: v for k, v in self._webhook_triggers.items() if v.rule_name != rule_name
                }
            elif isinstance(trigger, ChainTrigger):
                for source_rule in self._chain_triggers:
                    self._chain_triggers[source_rule] = [
                        t for t in self._chain_triggers[source_rule] if t.rule_name != rule_name
                    ]

        logger.info("Unregistered trigger for rule: %s", rule_name)
        return True

    def get_trigger(self, rule_name: str) -> BaseTrigger | None:
        """Get a trigger by rule name."""
        return self._triggers.get(rule_name)

    def handle_event(self, event_payload: Mapping[str, Any]) -> list[str]:
        """Dispatch an event to matching event triggers.

        Args:
            event_payload: The incoming event payload

        Returns:
            List of rule names that were triggered
        """
        triggered_rules = []
        for trigger in self._event_triggers:
            if trigger.enabled and trigger.handle_event(event_payload):
                triggered_rules.append(trigger.rule_name)
        return triggered_rules

    def handle_webhook(
        self,
        path: str,
        method: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[bool, str, str | None]:
        """Handle an incoming webhook request.

        Args:
            path: Request path
            method: HTTP method
            payload: Request payload
            headers: Request headers

        Returns:
            Tuple of (success, message, rule_name)
        """
        trigger = self._webhook_triggers.get(path)
        if not trigger:
            return False, "Webhook not found", None

        if not trigger.enabled:
            return False, "Webhook disabled", trigger.rule_name

        success, message = trigger.handle_request(method, payload, headers)
        return success, message, trigger.rule_name

    def fire_manual(
        self,
        rule_name: str,
        params: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> tuple[bool, str]:
        """Fire a manual trigger.

        Args:
            rule_name: Name of the rule to trigger
            params: Parameters to pass
            user_id: ID of user triggering

        Returns:
            Tuple of (success, message)
        """
        trigger = self._triggers.get(rule_name)
        if not trigger:
            return False, f"Rule not found: {rule_name}"

        if not isinstance(trigger, ManualTrigger):
            # Allow triggering any rule manually
            context = TriggerContext(
                trigger_type=TriggerType.MANUAL,
                trigger_id=f"{rule_name}_{int(time.time())}",
                payload=params or {},
                metadata={"user_id": user_id, "manual": True},
            )
            trigger.trigger(context)
            return True, "OK"

        return trigger.fire(params, user_id)

    def notify_rule_completed(
        self,
        rule_name: str,
        success: bool,
        result: dict[str, Any] | None = None,
    ) -> list[str]:
        """Notify chain triggers that a rule completed.

        Args:
            rule_name: Name of the completed rule
            success: Whether the rule succeeded
            result: Rule execution result

        Returns:
            List of chained rules that were triggered
        """
        triggered_rules = []
        chain_triggers = self._chain_triggers.get(rule_name, [])

        for trigger in chain_triggers:
            if trigger.enabled and trigger.on_rule_completed(rule_name, success, result):
                triggered_rules.append(trigger.rule_name)

        return triggered_rules

    def get_webhook_paths(self) -> list[str]:
        """Get all registered webhook paths."""
        return list(self._webhook_triggers.keys())

    def get_manual_parameters(self, rule_name: str) -> list[dict[str, Any]]:
        """Get manual trigger parameters for a rule."""
        trigger = self._triggers.get(rule_name)
        if isinstance(trigger, ManualTrigger):
            return trigger.get_parameter_schema()
        return []

    def shutdown(self) -> None:
        """Stop all triggers."""
        with self._lock:
            for trigger in self._triggers.values():
                try:
                    trigger.stop()
                except Exception as e:
                    logger.debug(
                        "Failed to stop trigger %s: %s",
                        trigger.rule_name,
                        e,
                    )
            self._triggers.clear()
            self._event_triggers.clear()
            self._webhook_triggers.clear()
            self._chain_triggers.clear()


__all__ = [
    "TriggerType",
    "TriggerContext",
    "BaseTrigger",
    "ScheduleTrigger",
    "EventTrigger",
    "WebhookTrigger",
    "ManualTrigger",
    "ChainTrigger",
    "TriggerRegistry",
]
