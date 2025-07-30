"""Tests for deployment info utilities."""

from datetime import datetime
import os
from unittest.mock import patch

import pytest

from trendsearth_ui.utils.deployment_info import get_deployment_info, get_health_response


def test_get_deployment_info_with_env_vars():
    """Test deployment info when environment variables are set."""
    with patch.dict(
        os.environ,
        {"GIT_BRANCH": "main", "GIT_COMMIT": "abc123def456", "DEPLOYMENT_ENVIRONMENT": "staging"},
    ):
        info = get_deployment_info()
        assert info["branch"] == "main"
        assert info["commit_sha"] == "abc123def456"
        assert info["environment"] == "staging"


def test_get_deployment_info_defaults():
    """Test deployment info with default values."""
    with patch.dict(os.environ, {}, clear=True):
        info = get_deployment_info()
        assert info["branch"] == "unknown"
        assert info["commit_sha"] == "unknown"
        assert info["environment"] == "development"


def test_get_deployment_info_aws_detection():
    """Test that AWS environment is detected."""
    with patch.dict(
        os.environ,
        {"AWS_REGION": "us-east-1", "GIT_BRANCH": "master", "GIT_COMMIT": "xyz789"},
        clear=True,
    ):
        info = get_deployment_info()
        assert info["environment"] == "production"


def test_get_deployment_info_ecs_detection():
    """Test that ECS environment is detected."""
    with patch.dict(
        os.environ,
        {
            "ECS_CONTAINER_METADATA_URI": "http://169.254.170.2/v2/metadata",
            "GIT_BRANCH": "master",
            "GIT_COMMIT": "xyz789",
        },
        clear=True,
    ):
        info = get_deployment_info()
        assert info["environment"] == "production"


def test_get_health_response():
    """Test health response structure."""
    with patch.dict(
        os.environ,
        {
            "GIT_BRANCH": "test-branch",
            "GIT_COMMIT": "test-commit",
            "DEPLOYMENT_ENVIRONMENT": "test",
        },
    ):
        response = get_health_response()

        # Check structure
        assert "deployment" in response
        assert "status" in response
        assert "timestamp" in response

        # Check deployment info
        assert response["deployment"]["branch"] == "test-branch"
        assert response["deployment"]["commit_sha"] == "test-commit"
        assert response["deployment"]["environment"] == "test"

        # Check status
        assert response["status"] == "ok"

        # Check timestamp format (ISO 8601)
        timestamp = response["timestamp"]
        assert timestamp.endswith("+00:00")  # UTC timezone
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def test_environment_precedence():
    """Test environment variable precedence."""
    with patch.dict(
        os.environ,
        {"DEPLOYMENT_ENVIRONMENT": "staging", "ENVIRONMENT": "development", "ENV": "test"},
    ):
        info = get_deployment_info()
        assert info["environment"] == "staging"

    with patch.dict(os.environ, {"ENVIRONMENT": "development", "ENV": "test"}, clear=True):
        info = get_deployment_info()
        assert info["environment"] == "development"

    with patch.dict(os.environ, {"ENV": "test"}, clear=True):
        info = get_deployment_info()
        assert info["environment"] == "test"
