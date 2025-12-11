"""Automation engine responsible for declarative workflows."""

from __future__ import annotations

import copy
import time
from collections.abc import Callable, Mapping
from functools import partial
from string import Template
from typing import Any

import httpx

from ..core.config import (
    AutomationActionConfig,
    AutomationRule,
    HTTPClientConfig,
    HTTPRequestConfig,
)
from ..core.logger import get_logger
from ..core.provider import BaseProvider
from ..core.templates import RenderedTemplate, TemplateRegistry
from ..scheduler import TaskScheduler

logger = get_logger("automation")


class AutomationEngine:
    """Coordinates automation rules using the scheduler and webhook clients/providers."""

    def __init__(
        self,
        rules: list[AutomationRule],
        scheduler: TaskScheduler | None,
        clients: Mapping[str, Any],
        template_registry: TemplateRegistry | None,
        http_defaults: HTTPClientConfig,
        send_text: Callable[[str, str], None],
        send_rendered: Callable[[RenderedTemplate, list[str]], None],
        providers: Mapping[str, BaseProvider] | None = None,
    ) -> None:
        self._rules = rules
        self._scheduler = scheduler
        self._clients = clients
        self._providers = providers or {}
        self._template_registry = template_registry
        self._http_defaults = http_defaults
        self._send_text = send_text
        self._send_rendered = send_rendered
        self._registered_jobs: set[str] = set()
        self._execution_history: list[dict[str, Any]] = []
        self._max_history: int = 100

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Register scheduled jobs for automation rules."""

        if not self._scheduler:
            schedule_rules = [
                r.name for r in self._rules if r.trigger.type == "schedule" and r.enabled
            ]
            if schedule_rules:
                logger.warning(
                    "Scheduler disabled but automation rules require it: %s",
                    ", ".join(schedule_rules),
                )
            return

        for rule in self._rules:
            if not rule.enabled or rule.trigger.type != "schedule":
                continue
            self._register_schedule(rule)

    def shutdown(self) -> None:
        """Remove registered automation jobs from the scheduler."""

        if not self._scheduler:
            return
        for job_id in list(self._registered_jobs):
            try:
                self._scheduler.remove_job(job_id)
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.debug("Failed to remove automation job %s: %s", job_id, exc)
            finally:
                self._registered_jobs.discard(job_id)

    # ------------------------------------------------------------------
    # Scheduling helpers
    # ------------------------------------------------------------------
    def _register_schedule(self, rule: AutomationRule) -> None:
        if not self._scheduler:
            raise RuntimeError("Scheduler instance is not available")
        assert rule.trigger.schedule is not None
        trigger_cfg = rule.trigger.schedule
        trigger_type = trigger_cfg.mode
        trigger_args = trigger_cfg.arguments

        job_id = f"automation.{rule.name}"
        runner = partial(self.execute_rule, rule, event_payload=None)
        try:
            job_id = self._scheduler.add_job(
                runner,
                trigger=trigger_type,
                job_id=job_id,
                replace_existing=True,
                **trigger_args,
            )
            self._registered_jobs.add(job_id)
            logger.info(
                "Registered automation schedule '%s' with trigger %s", rule.name, trigger_type
            )
        except Exception as exc:
            logger.error("Failed to register automation '%s': %s", rule.name, exc, exc_info=True)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    def handle_event(self, event_payload: Mapping[str, Any]) -> None:
        """Dispatch an incoming event to matching automation rules."""

        for rule in self._rules:
            if not rule.enabled or rule.trigger.type != "event":
                continue
            event_cfg = rule.trigger.event
            if not event_cfg:
                continue
            if event_cfg.event_type:
                event_type = self._extract(event_payload, "header.event_type")
                if event_type != event_cfg.event_type:
                    continue
            if not self._conditions_match(event_cfg.conditions, event_payload):
                continue
            self.execute_rule(rule, event_payload=event_payload)

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------
    def execute_rule(
        self,
        rule: AutomationRule,
        event_payload: Mapping[str, Any] | None,
    ) -> None:
        """Execute all actions for a rule with the provided context."""

        logger.debug("Executing automation rule '%s'", rule.name)
        context: dict[str, Any] = copy.deepcopy(rule.default_context)
        if event_payload is not None:
            context.setdefault("event", event_payload)

        for action in rule.actions:
            action_context = self._merge_context(context, action.context)
            try:
                self._execute_action(rule, action, action_context)
            except Exception as exc:
                logger.error(
                    "Automation '%s' action '%s' failed: %s",
                    rule.name,
                    action.type,
                    exc,
                    exc_info=True,
                )
            else:
                context.update(action_context)

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------
    def _get_client_or_provider(self, name: str) -> Any:
        """Get a client or provider by name.

        First checks providers, then falls back to legacy clients.

        Args:
            name: Client or provider name

        Returns:
            Client or provider instance, or None if not found
        """
        if name in self._providers:
            return self._providers[name]
        return self._clients.get(name)

    def _validate_targets(self, targets: list[str], rule_name: str) -> list[str]:
        """Validate that all target names exist as clients or providers.

        Args:
            targets: List of target names
            rule_name: Rule name for error messages

        Returns:
            Validated list of targets

        Raises:
            ValueError: If any target is not found
        """
        missing = []
        for name in targets:
            if name not in self._providers and name not in self._clients:
                missing.append(name)
        if missing:
            raise ValueError(
                f"Unknown webhook/provider(s) for automation '{rule_name}': {', '.join(missing)}"
            )
        return targets

    def _execute_action(
        self,
        rule: AutomationRule,
        action: AutomationActionConfig,
        context: dict[str, Any],
    ) -> None:
        targets = action.webhooks or rule.default_webhooks or ["default"]
        targets = self._validate_targets(targets, rule.name)

        if action.type == "send_text":
            text = action.text
            if action.template:
                rendered = self._render_template(action.template, context)
                text = rendered.content if rendered else text
                if rendered and rendered.type != "text":
                    # Treat as fully rendered template dispatch
                    self._send_rendered(rendered, targets)
                    return
            if text is None:
                raise ValueError("Resolved text for send_text action is empty")
            for webhook in targets:
                self._send_text(text, webhook)
            return

        if action.type == "send_template":
            rendered = self._render_template(action.template or "", context)
            if rendered is None:
                raise ValueError(f"Template '{action.template}' could not be rendered")
            self._send_rendered(rendered, targets)
            return

        if action.type == "http_request" and action.request:
            response_payload = self._perform_http_request(action.request, context)
            if action.request.save_as:
                context[action.request.save_as] = response_payload
            return

        raise ValueError(f"Unsupported automation action type: {action.type}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _render_template(
        self, template_name: str, context: Mapping[str, Any]
    ) -> RenderedTemplate | None:
        if not self._template_registry:
            logger.warning("Template '%s' requested but no templates configured", template_name)
            return None
        return self._template_registry.render(template_name, context)

    def _perform_http_request(
        self, request_config: HTTPRequestConfig, context: Mapping[str, Any]
    ) -> Any:
        payload = self._resolve_request_payload(request_config, context)
        retry = payload.retry or self._http_defaults.retry
        timeout_value = payload.timeout or self._http_defaults.timeout

        attempt = 0
        delay = retry.backoff_seconds
        while True:
            attempt += 1
            try:
                logger.debug(
                    "Automation HTTP request %s %s (attempt %s)",
                    payload.method,
                    payload.url,
                    attempt,
                )
                with httpx.Client(timeout=timeout_value) as client:
                    response = client.request(
                        payload.method,
                        payload.url,
                        headers=payload.headers,
                        params=payload.params,
                        json=payload.json_body,
                        data=payload.data_body,
                    )
                response.raise_for_status()
                if "application/json" in response.headers.get("content-type", ""):
                    return response.json()
                return response.text
            except Exception as exc:
                if attempt >= retry.max_attempts:
                    raise
                sleep_for = min(delay, retry.max_backoff_seconds)
                logger.warning(
                    "Automation HTTP request retry (%s/%s) after error: %s",
                    attempt,
                    retry.max_attempts,
                    exc,
                )
                time.sleep(sleep_for)
                delay = max(delay * retry.backoff_multiplier, retry.backoff_seconds)

    def _resolve_request_payload(
        self, request_config: HTTPRequestConfig, context: Mapping[str, Any]
    ) -> HTTPRequestConfig:
        payload = request_config.model_copy(deep=True)
        payload.url = self._interpolate(payload.url, context)
        payload.headers = {
            key: self._interpolate(value, context) for key, value in payload.headers.items()
        }
        payload.params = self._interpolate_mapping(payload.params, context)
        if payload.json_body is not None:
            payload.json_body = self._interpolate_mapping(payload.json_body, context)
        if payload.data_body is not None:
            payload.data_body = self._interpolate_mapping(payload.data_body, context)
        return payload

    def _interpolate(self, value: Any, context: Mapping[str, Any]) -> Any:
        if isinstance(value, str):
            return Template(value).safe_substitute(**context)
        return value

    def _interpolate_mapping(
        self, value: Mapping[str, Any] | list[Any], context: Mapping[str, Any]
    ) -> Any:
        if isinstance(value, dict):
            return {k: self._interpolate(v, context) for k, v in value.items()}
        if isinstance(value, list):
            return [self._interpolate(v, context) for v in value]
        return self._interpolate(value, context)

    @staticmethod
    def _merge_context(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        merged.update(override)
        return merged

    @staticmethod
    def _extract(payload: Mapping[str, Any], path: str) -> Any:
        current: Any = payload
        for part in path.split("."):
            if isinstance(current, Mapping):
                current = current.get(part)
            else:
                return None
        return current

    def _conditions_match(
        self,
        conditions: list[Any],
        payload: Mapping[str, Any],
    ) -> bool:
        for condition in conditions:
            value = self._extract(payload, condition.path)
            if condition.equals is not None and value != condition.equals:
                return False
            if condition.contains is not None and (
                not isinstance(value, str) or condition.contains not in value
            ):
                return False
        return True

    # ------------------------------------------------------------------
    # Rule management and triggering
    # ------------------------------------------------------------------
    def get_rule(self, rule_name: str) -> AutomationRule | None:
        """Get a rule by name.

        Args:
            rule_name: Name of the rule to find

        Returns:
            AutomationRule if found, None otherwise
        """
        for rule in self._rules:
            if rule.name == rule_name:
                return rule
        return None

    def get_rules(self) -> list[AutomationRule]:
        """Get all automation rules.

        Returns:
            List of all automation rules
        """
        return list(self._rules)

    def trigger_rule(
        self,
        rule_name: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Manually trigger an automation rule by name.

        Args:
            rule_name: Name of the rule to trigger
            context: Optional context to pass to the rule

        Returns:
            Execution result dictionary with success status and details
        """
        import time as time_module
        from datetime import datetime

        result: dict[str, Any] = {
            "rule_name": rule_name,
            "success": False,
            "triggered_at": datetime.now().isoformat(),
            "error": None,
            "actions_executed": 0,
        }

        rule = self.get_rule(rule_name)
        if not rule:
            result["error"] = f"Rule not found: {rule_name}"
            logger.warning("Attempted to trigger non-existent rule: %s", rule_name)
            return result

        if not rule.enabled:
            result["error"] = f"Rule is disabled: {rule_name}"
            logger.warning("Attempted to trigger disabled rule: %s", rule_name)
            return result

        start_time = time_module.time()
        try:
            event_payload = context if context else {}
            self.execute_rule(rule, event_payload=event_payload)
            result["success"] = True
            result["actions_executed"] = len(rule.actions)
            logger.info("Manually triggered automation rule: %s", rule_name)
        except Exception as exc:
            result["error"] = str(exc)
            logger.error("Failed to trigger rule %s: %s", rule_name, exc, exc_info=True)

        result["duration"] = time_module.time() - start_time

        # Record execution history
        self._record_execution(result)

        return result

    def enable_rule(self, rule_name: str) -> bool:
        """Enable an automation rule.

        Args:
            rule_name: Name of the rule to enable

        Returns:
            True if rule was enabled, False if not found
        """
        rule = self.get_rule(rule_name)
        if not rule:
            return False
        rule.enabled = True
        logger.info("Enabled automation rule: %s", rule_name)
        return True

    def disable_rule(self, rule_name: str) -> bool:
        """Disable an automation rule.

        Args:
            rule_name: Name of the rule to disable

        Returns:
            True if rule was disabled, False if not found
        """
        rule = self.get_rule(rule_name)
        if not rule:
            return False
        rule.enabled = False
        logger.info("Disabled automation rule: %s", rule_name)
        return True

    def _record_execution(self, result: dict[str, Any]) -> None:
        """Record an execution result to history.

        Args:
            result: Execution result dictionary
        """
        self._execution_history.append(result)
        # Trim history if needed
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]

    def get_execution_history(
        self,
        rule_name: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get execution history for automation rules.

        Args:
            rule_name: Optional filter by rule name
            limit: Maximum number of entries to return

        Returns:
            List of execution history entries (newest first)
        """
        history = self._execution_history
        if rule_name:
            history = [h for h in history if h.get("rule_name") == rule_name]
        return list(reversed(history[-limit:]))

    def get_rule_status(self, rule_name: str) -> dict[str, Any]:
        """Get detailed status for a rule.

        Args:
            rule_name: Name of the rule

        Returns:
            Status dictionary with rule details
        """
        rule = self.get_rule(rule_name)
        if not rule:
            return {"error": f"Rule not found: {rule_name}"}

        job_id = f"automation.{rule_name}"
        next_run = None
        if self._scheduler and job_id in self._registered_jobs:
            job = self._scheduler.get_job(job_id)
            if job:
                next_run = str(job.next_run_time) if job.next_run_time else None

        # Get recent executions for this rule
        recent_executions = self.get_execution_history(rule_name, limit=5)

        return {
            "name": rule.name,
            "description": rule.description,
            "enabled": rule.enabled,
            "trigger_type": rule.trigger.type,
            "actions_count": len(rule.actions),
            "registered": job_id in self._registered_jobs,
            "next_run": next_run,
            "recent_executions": recent_executions,
        }
