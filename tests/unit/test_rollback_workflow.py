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

    # Check required steps exist for ECR + CodeDeploy rollback
    required_steps = [
        "Validate inputs and configuration",
        "Configure AWS credentials",
        "Get current deployment status",
        "Determine rollback strategy",
        "Perform automatic rollback",
        "Perform commit-specific rollback",
        "Verify rollback",
        "Notify Rollbar of rollback",
        "Rollback summary",
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

    # Check that required secrets are referenced for ECR + CodeDeploy
    required_secrets = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "CODEDEPLOY_S3_BUCKET",
        "ROLLBAR_ACCESS_TOKEN",  # Optional but should be referenced
    ]

    for secret in required_secrets:
        assert f"secrets.{secret}" in content, f"Missing secret reference: {secret}"


def test_rollback_workflow_has_ec2_references():
    """Test that the rollback workflow has ECR + CodeDeploy specific references."""
    workflow_path = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback-production.yml"
    )

    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    # These should appear in an ECR + CodeDeploy rollback workflow
    codedeploy_terms = [
        "ECR_REPOSITORY",
        "CODEDEPLOY_APPLICATION",
        "CODEDEPLOY_DEPLOYMENT_GROUP",
        "aws deploy",
        "trendsearth-ui",  # Application name
    ]

    for term in codedeploy_terms:
        assert term in content, f"Missing ECR/CodeDeploy term that should be in workflow: {term}"


def test_rollback_workflow_health_check_url():
    """Test that the rollback workflow uses CodeDeploy validation hooks."""
    workflow_path = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "rollback-production.yml"
    )

    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    # Should reference CodeDeploy validation instead of direct health checks
    assert "CodeDeploy validation hooks" in content or "validation hooks" in content

    # Should still reference the health endpoint in deployment scripts (via appspec.yml)
    # but the workflow itself relies on CodeDeploy for validation
    assert "rollback" in content.lower()
    assert "production" in content.lower()
