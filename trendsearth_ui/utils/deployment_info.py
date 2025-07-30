"""Utilities for getting deployment information."""

from datetime import datetime, timezone
import os


def get_deployment_info():
    """Get deployment information including branch, commit, and environment."""
    # Get git information from environment variables (set during deployment)
    branch = os.environ.get("GIT_BRANCH", "unknown")
    commit_sha = os.environ.get("GIT_COMMIT", "unknown")

    # Determine environment - check various environment variables
    environment = (
        os.environ.get("DEPLOYMENT_ENVIRONMENT")
        or os.environ.get("ENVIRONMENT")
        or os.environ.get("ENV")
        or "development"  # Default fallback
    )

    # If we're running in production/staging, use those values
    # This can be set by deployment scripts or container orchestration
    if os.environ.get("AWS_REGION") or os.environ.get("ECS_CONTAINER_METADATA_URI"):
        environment = "production"

    return {"branch": branch, "commit_sha": commit_sha, "environment": environment}


def get_health_response():
    """Get the complete health check response with deployment info."""
    deployment_info = get_deployment_info()

    response = {
        "deployment": deployment_info,
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return response
