"""Tests for rollback workflow validation."""

from pathlib import Path
import subprocess
import sys


def test_rollback_workflow_syntax():
    """Test that the rollback workflow has valid YAML syntax."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback.yml"

    # Just check that the file can be read and has basic YAML structure
    with open(workflow_path) as f:
        content = f.read()

    # Basic YAML structure checks
    assert content.strip().startswith("name:")
    assert "on:" in content
    assert "jobs:" in content
    assert content.count(":") > 10  # Should have many key-value pairs


def test_rollback_workflow_structure():
    """Test that the rollback workflow has the expected structure."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback.yml"

    with open(workflow_path) as f:
        content = f.read()

    # Check basic structure exists
    assert "name: Rollback ECS Deployment" in content
    assert "workflow_dispatch:" in content
    assert "task_definition_revision:" in content
    assert "default: 'previous'" in content
    assert "jobs:" in content
    assert "rollback:" in content
    assert "runs-on: ubuntu-latest" in content
    assert "environment: production" in content


def test_rollback_workflow_required_steps():
    """Test that the rollback workflow has all required steps."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback.yml"

    with open(workflow_path) as f:
        content = f.read()

    # Check required steps exist
    required_steps = [
        "Configure AWS credentials",
        "Get current and target task definitions",
        "Rollback ECS service",
        "Wait for rollback to complete",
        "Get rollback deployment details",
        "Verify rollback",
        "Rollback notification",
        "Notify Rollbar of rollback",
    ]

    for required_step in required_steps:
        assert f"name: {required_step}" in content, f"Missing required step: {required_step}"


def test_rollback_workflow_secrets():
    """Test that the rollback workflow references the expected secrets."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback.yml"

    with open(workflow_path) as f:
        content = f.read()

    # Check that required secrets are referenced
    required_secrets = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "ECS_CLUSTER",
        "ECS_SERVICE",
        "ROLLBAR_ACCESS_TOKEN",  # Optional but should be referenced
    ]

    for secret in required_secrets:
        assert f"secrets.{secret}" in content, f"Missing secret reference: {secret}"


def test_rollback_workflow_no_ec2_references():
    """Test that the rollback workflow has no EC2-specific references."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback.yml"

    with open(workflow_path) as f:
        content = f.read()

    # These should not appear in an ECS rollback workflow
    ec2_terms = [
        "ssh",
        "systemctl",
        "EC2_HOST",
        "EC2_USER",
        ":8050",  # Wrong port for ECS deployment
        "ln -sfn",  # Symlink operations
        "sudo",
    ]

    for term in ec2_terms:
        assert term not in content, (
            f"Found EC2-specific term that should not be in ECS workflow: {term}"
        )


def test_rollback_workflow_health_check_url():
    """Test that the rollback workflow uses the correct health check endpoint."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback.yml"

    with open(workflow_path) as f:
        content = f.read()

    # Should use correct health endpoint and load balancer URL approach
    assert "/api-ui-health" in content
    assert "LB_URL" in content  # Uses load balancer URL variable
    assert ":8050" not in content  # Wrong port for ECS deployment

    # Should use the same URL pattern as deploy workflow
    assert "http://$LB_URL/api-ui-health" in content
