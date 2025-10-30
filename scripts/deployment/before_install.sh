#!/bin/bash

# Before Install Script for CodeDeploy
# Prepares the environment for deployment

set -e

echo "🔧 Before Install: Preparing environment for deployment"

# Get environment from deployment group name or default to production
if [[ "${DEPLOYMENT_GROUP_NAME}" == *"staging"* ]]; then
    ENVIRONMENT="staging"
    APP_PATH="/opt/trends-earth-ui-staging"
    STACK_NAME="trendsearth-api-ui-staging"
else
    ENVIRONMENT="production"
    APP_PATH="/opt/trends-earth-ui"
    STACK_NAME="trendsearth-api-ui-prod"
fi

echo "Environment: $ENVIRONMENT"
echo "App Path: $APP_PATH"
echo "Stack Name: $STACK_NAME"

# Create application directory if it doesn't exist
mkdir -p "$APP_PATH"

# Ensure Docker is running
echo "🐳 Ensuring Docker is running..."
systemctl start docker
systemctl enable docker

# Wait for Docker to be ready
while ! docker info >/dev/null 2>&1; do
    echo "Waiting for Docker to be ready..."
    sleep 2
done

echo "✅ Docker is ready"

# Configure ECR authentication
echo "🔐 Configuring ECR authentication..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Login to ECR
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "✅ ECR authentication configured"

# Export environment variables for later scripts
echo "export ENVIRONMENT=$ENVIRONMENT" > /opt/deploy-env
echo "export APP_PATH=$APP_PATH" >> /opt/deploy-env
echo "export STACK_NAME=$STACK_NAME" >> /opt/deploy-env
echo "export ECR_REGISTRY=$ECR_REGISTRY" >> /opt/deploy-env
echo "export AWS_REGION=$AWS_REGION" >> /opt/deploy-env
echo "export IMAGE_REPOSITORY=trendsearth-api-ui" >> /opt/deploy-env

# Load deployment metadata from the bundle if available so downstream steps
# can reference the exact image and branch that were built in CI.
BUNDLE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEPLOYMENT_INFO_FILE="$BUNDLE_ROOT/deployment-info.json"

if [ -f "$DEPLOYMENT_INFO_FILE" ]; then
    echo "🧾 Loading deployment metadata from deployment-info.json"

    DEPLOYMENT_IMAGE=""
    BRANCH_NAME_METADATA=""
    DEPLOYMENT_COMMIT=""

    if command -v python3 >/dev/null 2>&1; then
        mapfile -t _DEPLOYMENT_METADATA < <(python3 - "$DEPLOYMENT_INFO_FILE" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as fp:
    info = json.load(fp)
print(info.get("image", ""))
print(info.get("branch", ""))
print(info.get("deploymentId", ""))
PY
        )
        DEPLOYMENT_IMAGE="${_DEPLOYMENT_METADATA[0]}"
        BRANCH_NAME_METADATA="${_DEPLOYMENT_METADATA[1]}"
        DEPLOYMENT_COMMIT="${_DEPLOYMENT_METADATA[2]}"
    else
        DEPLOYMENT_IMAGE=$(grep '"image"' "$DEPLOYMENT_INFO_FILE" | head -n1 | sed 's/.*"image"[[:space:]]*:[[:space:]]*"//; s/".*//')
        BRANCH_NAME_METADATA=$(grep '"branch"' "$DEPLOYMENT_INFO_FILE" | head -n1 | sed 's/.*"branch"[[:space:]]*:[[:space:]]*"//; s/".*//')
        DEPLOYMENT_COMMIT=$(grep '"deploymentId"' "$DEPLOYMENT_INFO_FILE" | head -n1 | sed 's/.*"deploymentId"[[:space:]]*:[[:space:]]*"//; s/".*//')
    fi

    if [ -n "$DEPLOYMENT_IMAGE" ]; then
        IMAGE_TAG_FROM_METADATA="${DEPLOYMENT_IMAGE##*:}"
        echo "  • Image: $DEPLOYMENT_IMAGE"
        echo "export DEPLOYMENT_IMAGE=$DEPLOYMENT_IMAGE" >> /opt/deploy-env
        if [ -n "$IMAGE_TAG_FROM_METADATA" ] && [ "$IMAGE_TAG_FROM_METADATA" != "$DEPLOYMENT_IMAGE" ]; then
            echo "  • Image tag: $IMAGE_TAG_FROM_METADATA"
            echo "export IMAGE_TAG=$IMAGE_TAG_FROM_METADATA" >> /opt/deploy-env
        fi

        REPO_WITH_TAG="${DEPLOYMENT_IMAGE##*/}"
        REPO_FROM_METADATA="${REPO_WITH_TAG%%:*}"
        if [ -n "$REPO_FROM_METADATA" ]; then
            echo "  • Repository: $REPO_FROM_METADATA"
            echo "export IMAGE_REPOSITORY=$REPO_FROM_METADATA" >> /opt/deploy-env
        fi
    fi

    if [ -n "$BRANCH_NAME_METADATA" ]; then
        echo "  • Branch: $BRANCH_NAME_METADATA"
        echo "export BRANCH_NAME=$BRANCH_NAME_METADATA" >> /opt/deploy-env
    fi

    if [ -n "$DEPLOYMENT_COMMIT" ]; then
        echo "  • Commit: $DEPLOYMENT_COMMIT"
        echo "export GIT_COMMIT_SHA=$DEPLOYMENT_COMMIT" >> /opt/deploy-env
    fi
else
    echo "ℹ️ deployment-info.json not found; default image tag will be used"
fi

echo "✅ Before Install completed successfully"