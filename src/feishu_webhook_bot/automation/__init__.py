"""Automation engine for declarative workflows.

This module provides:
- AutomationEngine: Main engine for coordinating automation rules
- Action executors for various action types (send_text, http_request, plugin_method, etc.)
- Trigger system for schedule, event, webhook, manual, and chain triggers
- Workflow orchestration with dependencies and parallel execution
"""

from .actions import (
    ActionExecutorFactory,
    ActionResult,
    ActionType,
    BaseActionExecutor,
    ConditionalExecutor,
    DelayExecutor,
    LogExecutor,
    LoopExecutor,
    NotifyExecutor,
    ParallelExecutor,
    PluginMethodExecutor,
    PythonCodeExecutor,
    SetVariableExecutor,
)
from .engine import AutomationEngine
from .triggers import (
    BaseTrigger,
    ChainTrigger,
    EventTrigger,
    ManualTrigger,
    ScheduleTrigger,
    TriggerContext,
    TriggerRegistry,
    TriggerType,
    WebhookTrigger,
)
from .workflow import (
    DependencyResolver,
    DependencyType,
    WorkflowExecution,
    WorkflowOrchestrator,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTemplate,
    WorkflowTemplateRegistry,
    create_default_template_registry,
)

__all__ = [
    # Engine
    "AutomationEngine",
    # Actions
    "ActionType",
    "ActionResult",
    "BaseActionExecutor",
    "ActionExecutorFactory",
    "PluginMethodExecutor",
    "PythonCodeExecutor",
    "ConditionalExecutor",
    "LoopExecutor",
    "SetVariableExecutor",
    "DelayExecutor",
    "NotifyExecutor",
    "LogExecutor",
    "ParallelExecutor",
    # Triggers
    "TriggerType",
    "TriggerContext",
    "BaseTrigger",
    "ScheduleTrigger",
    "EventTrigger",
    "WebhookTrigger",
    "ManualTrigger",
    "ChainTrigger",
    "TriggerRegistry",
    # Workflow
    "WorkflowStatus",
    "DependencyType",
    "WorkflowStep",
    "WorkflowExecution",
    "WorkflowTemplate",
    "DependencyResolver",
    "WorkflowOrchestrator",
    "WorkflowTemplateRegistry",
    "create_default_template_registry",
]
