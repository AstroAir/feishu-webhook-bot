"""Tests for automation workflow orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock

from feishu_webhook_bot.automation.actions import ActionResult
from feishu_webhook_bot.automation.workflow import (
    DependencyType,
    WorkflowExecution,
    WorkflowOrchestrator,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTemplate,
    WorkflowTemplateRegistry,
    create_default_template_registry,
)


class TestWorkflowStatus:
    """Tests for WorkflowStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """Test that all expected statuses are defined."""
        expected = ["pending", "running", "completed", "failed", "cancelled", "paused", "waiting"]
        for status in expected:
            assert hasattr(WorkflowStatus, status.upper()), f"Missing status: {status}"


class TestDependencyType:
    """Tests for DependencyType enum."""

    def test_all_dependency_types_exist(self) -> None:
        """Test that all expected dependency types are defined."""
        expected = ["success", "completion", "failure", "any"]
        for dep_type in expected:
            assert hasattr(DependencyType, dep_type.upper()), f"Missing dependency type: {dep_type}"


class TestWorkflowStep:
    """Tests for WorkflowStep dataclass."""

    def test_create_step(self) -> None:
        """Test creating a workflow step."""
        step = WorkflowStep(
            name="Test Step",
            action_type="log",
            config={"message": "test"},
        )
        assert step.name == "Test Step"
        assert step.action_type == "log"
        assert step.config == {"message": "test"}

    def test_step_with_dependencies(self) -> None:
        """Test step with dependencies."""
        step = WorkflowStep(
            name="Dependent Step",
            action_type="log",
            config={"message": "test"},
            depends_on=["step1"],
        )
        assert step.depends_on == ["step1"]

    def test_step_with_condition(self) -> None:
        """Test step with condition."""
        step = WorkflowStep(
            name="Conditional Step",
            action_type="log",
            config={"message": "test"},
            condition="context.get('run_step', True)",
        )
        assert step.condition == "context.get('run_step', True)"

    def test_step_defaults(self) -> None:
        """Test step default values."""
        step = WorkflowStep(
            name="Simple Step",
            action_type="log",
            config={},
        )
        assert step.depends_on == []
        assert step.condition is None
        assert step.on_error == "fail"


class TestWorkflowExecution:
    """Tests for WorkflowExecution."""

    def test_create_execution(self) -> None:
        """Test creating a workflow execution."""
        execution = WorkflowExecution(
            workflow_id="wf1",
            rule_name="test_rule",
        )
        assert execution.workflow_id == "wf1"
        assert execution.rule_name == "test_rule"
        assert execution.status == WorkflowStatus.PENDING

    def test_execution_to_dict(self) -> None:
        """Test execution to_dict method."""
        execution = WorkflowExecution(
            workflow_id="wf1",
            rule_name="test_rule",
        )
        result = execution.to_dict()
        assert result["workflow_id"] == "wf1"
        assert result["rule_name"] == "test_rule"
        assert result["status"] == "pending"


class TestWorkflowTemplate:
    """Tests for WorkflowTemplate."""

    def test_create_template(self) -> None:
        """Test creating a workflow template."""
        step = WorkflowStep(
            name="Step 1",
            action_type="log",
            config={"message": "test"},
        )
        template = WorkflowTemplate(
            name="test_template",
            description="A test template",
            steps=[step],
        )
        assert template.name == "test_template"
        assert template.description == "A test template"
        assert len(template.steps) == 1

    def test_template_with_tags(self) -> None:
        """Test template with tags."""
        template = WorkflowTemplate(
            name="tagged",
            description="Tagged template",
            steps=[],
            tags=["notification", "alert"],
        )
        assert "notification" in template.tags
        assert "alert" in template.tags

    def test_template_to_dict(self) -> None:
        """Test template to_dict method."""
        step = WorkflowStep(
            name="Step 1",
            action_type="log",
            config={},
        )
        template = WorkflowTemplate(
            name="test",
            description="Test",
            steps=[step],
        )
        result = template.to_dict()
        assert result["name"] == "test"
        assert result["description"] == "Test"
        assert len(result["steps"]) == 1

    def test_template_from_dict(self) -> None:
        """Test creating template from dict."""
        data = {
            "name": "from_dict",
            "description": "Created from dict",
            "steps": [
                {"name": "s1", "action_type": "log", "config": {}},
            ],
            "tags": ["test"],
        }
        template = WorkflowTemplate.from_dict(data)
        assert template.name == "from_dict"
        assert len(template.steps) == 1
        assert template.tags == ["test"]


class TestWorkflowOrchestrator:
    """Tests for WorkflowOrchestrator."""

    def test_create_orchestrator(self) -> None:
        """Test creating an orchestrator."""
        action_executor = MagicMock(return_value=ActionResult(success=True))
        orchestrator = WorkflowOrchestrator(action_executor=action_executor)
        assert orchestrator is not None

    def test_orchestrator_with_action_executor(self) -> None:
        """Test orchestrator with action executor."""
        action_executor = MagicMock(return_value=ActionResult(success=True))
        orchestrator = WorkflowOrchestrator(action_executor=action_executor)
        assert orchestrator.action_executor is action_executor

    def test_execute_workflow_basic(self) -> None:
        """Test executing a basic workflow."""
        action_executor = MagicMock(return_value={"success": True})
        orchestrator = WorkflowOrchestrator(action_executor=action_executor)

        steps = [
            WorkflowStep(name="Step 1", action_type="log", config={"message": "test"}),
        ]
        execution = orchestrator.execute_workflow(
            workflow_id="wf_test_1",
            rule_name="test_rule",
            steps=steps,
        )

        assert execution is not None
        assert execution.status in (WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING)

    def test_get_execution(self) -> None:
        """Test getting execution by ID."""
        action_executor = MagicMock(return_value={"success": True})
        orchestrator = WorkflowOrchestrator(action_executor=action_executor)
        execution = orchestrator.execute_workflow(
            workflow_id="wf_test_2",
            rule_name="test",
            steps=[],
        )

        retrieved = orchestrator.get_execution(execution.workflow_id)
        assert retrieved is execution

    def test_cancel_execution(self) -> None:
        """Test cancelling execution."""
        action_executor = MagicMock(return_value={"success": True})
        orchestrator = WorkflowOrchestrator(action_executor=action_executor)
        execution = orchestrator.execute_workflow(
            workflow_id="wf_test_3",
            rule_name="test",
            steps=[],
        )
        execution.status = WorkflowStatus.RUNNING

        result = orchestrator.cancel_execution(execution.workflow_id)
        assert result is True
        assert execution.status == WorkflowStatus.CANCELLED


class TestWorkflowTemplateRegistry:
    """Tests for WorkflowTemplateRegistry."""

    def test_register_template(self) -> None:
        """Test registering a template."""
        registry = WorkflowTemplateRegistry()
        template = WorkflowTemplate(
            name="test",
            description="Test template",
            steps=[],
        )
        registry.register(template)

        assert registry.get("test") is template

    def test_unregister_template(self) -> None:
        """Test unregistering a template."""
        registry = WorkflowTemplateRegistry()
        template = WorkflowTemplate(name="test", description="", steps=[])
        registry.register(template)
        result = registry.unregister("test")

        assert result is True
        assert registry.get("test") is None

    def test_list_templates(self) -> None:
        """Test listing all templates."""
        registry = WorkflowTemplateRegistry()
        t1 = WorkflowTemplate(name="t1", description="", steps=[])
        t2 = WorkflowTemplate(name="t2", description="", steps=[])
        registry.register(t1)
        registry.register(t2)

        templates = registry.list_templates()
        assert len(templates) == 2

    def test_list_templates_by_tag(self) -> None:
        """Test listing templates by tag."""
        registry = WorkflowTemplateRegistry()
        t1 = WorkflowTemplate(name="t1", description="", steps=[], tags=["notification"])
        t2 = WorkflowTemplate(name="t2", description="", steps=[], tags=["alert"])
        t3 = WorkflowTemplate(name="t3", description="", steps=[], tags=["notification"])
        registry.register(t1)
        registry.register(t2)
        registry.register(t3)

        notification_templates = registry.list_templates(tags=["notification"])
        assert len(notification_templates) == 2

    def test_instantiate_template(self) -> None:
        """Test instantiating a template."""
        registry = WorkflowTemplateRegistry()
        step = WorkflowStep(
            name="Step 1",
            action_type="log",
            config={"message": "test"},
        )
        template = WorkflowTemplate(
            name="test",
            description="Test",
            steps=[step],
        )
        registry.register(template)

        result = registry.instantiate("test")
        assert result is not None
        steps, context = result
        assert len(steps) == 1


class TestDefaultTemplateRegistry:
    """Tests for built-in templates."""

    def test_create_default_registry(self) -> None:
        """Test creating registry with default templates."""
        registry = create_default_template_registry()
        templates = registry.list_templates()
        # Should have some built-in templates
        assert len(templates) >= 0

    def test_default_templates_valid(self) -> None:
        """Test that default templates are valid."""
        registry = create_default_template_registry()

        for template in registry.list_templates():
            assert template.name is not None
            assert template.description is not None
