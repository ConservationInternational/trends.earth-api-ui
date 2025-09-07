"""Tests for rollback workflow validation."""

from pathlib import Path
import subprocess
import sys


def test_rollback_workflow_syntax():
    """Test that the rollback workflow has valid YAML syntax."""
    workflow_path = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback-production.yml"
    )

    # Just check that the file can be read and has basic YAML structure
    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    # Basic YAML structure checks
    assert content.strip().startswith("name:")
    assert "on:" in content
    assert "jobs:" in content
    assert content.count(":") > 10  # Should have many key-value pairs


def test_rollback_workflow_structure():
    """Test that the rollback workflow has the expected structure."""
    workflow_path = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback-production.yml"
    )

    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    # Check basic structure exists for EC2 Docker Swarm deployment
    assert "name: Rollback Production Deployment" in content
    assert "workflow_dispatch:" in content
    assert "rollback_to_commit:" in content
    assert "reason:" in content
    assert "jobs:" in content
    assert "rollback-production:" in content
    assert "runs-on: ubuntu-latest" in content
    assert "environment: production" in content


def test_rollback_workflow_required_steps():
    """Test that the rollback workflow has all required steps."""
    workflow_path = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback-production.yml"
    )

    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    # Check required steps exist for EC2 Docker Swarm rollback
    required_steps = [
        "Validate required secrets",
        "Configure AWS credentials",
        "Get runner IP and update security group",
        "Set SSH port variable",
        "Validate and prepare rollback target",
        "Perform production rollback",
        "Verify rollback health",
        "Run basic integration tests after rollback",
        "Notify Rollbar of rollback",
        "Cleanup security group access",
    ]

    for required_step in required_steps:
        assert f"name: {required_step}" in content, f"Missing required step: {required_step}"


def test_rollback_workflow_secrets():
    """Test that the rollback workflow references the expected secrets."""
    workflow_path = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback-production.yml"
    )

    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    # Check that required secrets are referenced for EC2 Docker Swarm
    required_secrets = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "DOCKER_REGISTRY",
        "PROD_HOST",
        "PROD_USERNAME",
        "PROD_SSH_KEY",
        "PROD_SECURITY_GROUP_ID",
        "ROLLBAR_ACCESS_TOKEN",  # Optional but should be referenced
    ]

    for secret in required_secrets:
        assert f"secrets.{secret}" in content, f"Missing secret reference: {secret}"


def test_rollback_workflow_has_ec2_references():
    """Test that the rollback workflow has EC2/Docker Swarm specific references."""
    workflow_path = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback-production.yml"
    )

    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    # These should appear in an EC2 Docker Swarm rollback workflow
    ec2_terms = [
        "ssh-action",
        "docker service",
        "appleboy/ssh-action",
        ":8000",  # Correct port for production
        "trendsearth-ui-prod",  # Stack name
    ]

    for term in ec2_terms:
        assert term in content, f"Missing EC2/Docker Swarm term that should be in workflow: {term}"


def test_rollback_workflow_health_check_url():
    """Test that the rollback workflow uses the correct health check endpoint."""
    workflow_path = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback-production.yml"
    )

    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    # Should use correct health endpoint for EC2 deployment
    assert "/api-ui-health" in content
    assert ":8000" in content  # Production port
    assert "127.0.0.1:8000" in content  # Direct localhost check

    # Should use the direct URL pattern for EC2
    assert "http://127.0.0.1:8000/api-ui-health" in content
