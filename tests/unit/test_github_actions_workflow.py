"""Tests for GitHub Actions workflow validation."""

from pathlib import Path

import pytest
import yaml


class TestGitHubActionsWorkflow:
    """Test suite for GitHub Actions workflow file validation."""

    def test_workflow_file_exists(self):
        """Test that the sync workflow file exists."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"
        assert workflow_path.exists(), f"Workflow file not found at {workflow_path}"

    def test_workflow_syntax_valid(self):
        """Test that the workflow YAML syntax is valid."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"

        # Skip if workflow doesn't exist yet
        if not workflow_path.exists():
            pytest.skip("Workflow file not created yet")

        # Parse YAML to validate syntax
        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)

        # Basic validation - must be a dict
        assert isinstance(workflow, dict), "Workflow must be a YAML dictionary"
        assert "name" in workflow, "Workflow must have a name"
        assert "on" in workflow, "Workflow must have trigger configuration"
        assert "jobs" in workflow, "Workflow must define jobs"

    def test_workflow_has_required_triggers(self):
        """Test that workflow has schedule and workflow_dispatch triggers."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"

        if not workflow_path.exists():
            pytest.skip("Workflow file not created yet")

        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)

        triggers = workflow.get("on", {})

        # Must support scheduled execution (cron)
        assert "schedule" in triggers, "Workflow must support scheduled execution"
        assert isinstance(triggers["schedule"], list), "Schedule must be a list"
        assert len(triggers["schedule"]) > 0, "Schedule must have at least one cron entry"

        # Must support manual execution
        assert "workflow_dispatch" in triggers, "Workflow must support manual triggers"

    def test_workflow_schedule_syntax_valid(self):
        """Test that cron schedule syntax is valid."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"

        if not workflow_path.exists():
            pytest.skip("Workflow file not created yet")

        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)

        schedule = workflow["on"]["schedule"]

        # Each schedule entry must have a 'cron' field
        for entry in schedule:
            assert "cron" in entry, "Each schedule entry must have a cron field"
            cron = entry["cron"]
            assert isinstance(cron, str), "Cron must be a string"
            # Basic cron format validation (5 fields)
            parts = cron.split()
            assert len(parts) == 5, f"Cron must have 5 fields, got {len(parts)}: {cron}"

    def test_workflow_has_sync_job(self):
        """Test that workflow defines a sync job."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"

        if not workflow_path.exists():
            pytest.skip("Workflow file not created yet")

        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)

        jobs = workflow["jobs"]
        assert "sync" in jobs, "Workflow must have a 'sync' job"

        sync_job = jobs["sync"]
        assert "runs-on" in sync_job, "Sync job must specify runs-on"
        assert "steps" in sync_job, "Sync job must define steps"
        assert len(sync_job["steps"]) > 0, "Sync job must have at least one step"

    def test_workflow_uses_secrets_for_credentials(self):
        """Test that workflow uses GitHub secrets for sensitive data."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"

        if not workflow_path.exists():
            pytest.skip("Workflow file not created yet")

        with open(workflow_path) as f:
            content = f.read()

        # Workflow should reference secrets (not hardcoded tokens)
        assert "secrets." in content, "Workflow must use GitHub secrets"

        # Should NOT contain hardcoded tokens
        assert "ghp_" not in content, "Workflow must not contain hardcoded GitHub tokens"
        assert "glpat-" not in content, "Workflow must not contain hardcoded GitLab tokens"

    def test_workflow_has_python_setup(self):
        """Test that workflow sets up Python environment."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"

        if not workflow_path.exists():
            pytest.skip("Workflow file not created yet")

        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)

        sync_job = workflow["jobs"]["sync"]
        steps = sync_job["steps"]

        # Look for Python setup action
        python_setup_found = False
        for step in steps:
            if "uses" in step and "setup-python" in step["uses"]:
                python_setup_found = True
                break

        assert python_setup_found, "Workflow must set up Python environment"

    def test_workflow_installs_dependencies(self):
        """Test that workflow installs project dependencies."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"

        if not workflow_path.exists():
            pytest.skip("Workflow file not created yet")

        with open(workflow_path) as f:
            content = f.read()

        # Should install requirements
        assert "pip install" in content, "Workflow must install dependencies"

    def test_workflow_runs_sync_command(self):
        """Test that workflow executes the sync command."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"

        if not workflow_path.exists():
            pytest.skip("Workflow file not created yet")

        with open(workflow_path) as f:
            content = f.read()

        # Should run repo-cloner sync command
        assert "repo-cloner sync" in content or "python -m repo_cloner" in content, \
            "Workflow must execute sync command"

    def test_workflow_dispatch_has_input_options(self):
        """Test that workflow_dispatch allows input configuration."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sync.yml"

        if not workflow_path.exists():
            pytest.skip("Workflow file not created yet")

        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)

        workflow_dispatch = workflow["on"]["workflow_dispatch"]

        # Should have inputs for configuration
        assert "inputs" in workflow_dispatch, "workflow_dispatch should allow inputs"
        inputs = workflow_dispatch["inputs"]

        # Should at least have config_path or similar
        assert len(inputs) > 0, "workflow_dispatch should have at least one input option"
