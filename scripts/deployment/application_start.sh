#!/bin/bash

# Application Start Script for CodeDeploy
# Starts the new deployment using Docker Swarm

set -e

echo "🚀 Application Start: Starting new deployment"

# Load environment variables
source /opt/deploy-env

echo "Environment: $ENVIRONMENT"
echo "App Path: $APP_PATH"
echo "Stack Name: $STACK_NAME"
APP_IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-trendsearth-api-ui}"
echo "Image Repository: $APP_IMAGE_REPOSITORY"

# Short-circuit if this node is not the active swarm manager. CodeDeploy may target
# multiple nodes for redundancy, but only the current leader should run stack updates.
echo "🔍 Checking swarm manager status..."
if ! docker info >/dev/null 2>&1; then
    echo "⚠️ Docker daemon unreachable. Skipping deployment on this node."
    exit 0
fi

manager_status=$(docker node ls --format '{{.Self}} {{.ManagerStatus}}' 2>/dev/null | awk '$1=="true" {print $2}')
if [ -z "$manager_status" ]; then
    echo "ℹ️ This node is not part of the swarm or manager status unknown. Skipping."
    exit 0
fi

if [ "$manager_status" != "Leader" ]; then
    echo "ℹ️ Node is a swarm manager but not the leader ($manager_status). Skipping deployment."
    exit 0
fi

echo "✅ Node is the active swarm leader. Continuing deployment."

# Navigate to application directory
cd "$APP_PATH"

# Set compose file based on environment
if [ "$ENVIRONMENT" = "staging" ]; then
    COMPOSE_FILE="docker-compose.staging.yml"
    COMPOSE_IMAGE_TAG="staging"
else
    COMPOSE_FILE="docker-compose.prod.yml"
    COMPOSE_IMAGE_TAG="latest"
fi

# Prefer the exact image tag provided by CI metadata; fall back to the
# CodeDeploy deployment ID and ultimately to "latest" if needed.
if [ -n "${IMAGE_TAG:-}" ]; then
    RESOLVED_IMAGE_TAG="$IMAGE_TAG"
elif [ -n "${DEPLOYMENT_IMAGE:-}" ]; then
    RESOLVED_IMAGE_TAG="${DEPLOYMENT_IMAGE##*:}"
elif [ -n "${DEPLOYMENT_ID:-}" ]; then
    RESOLVED_IMAGE_TAG="$DEPLOYMENT_ID"
else
    RESOLVED_IMAGE_TAG="latest"
fi

IMAGE_TAG="$RESOLVED_IMAGE_TAG"

echo "Compose File: $COMPOSE_FILE"
echo "Image Tag: $IMAGE_TAG"
echo "Compose Image Tag: $COMPOSE_IMAGE_TAG"

# Update compose file with ECR registry
export DOCKER_REGISTRY="$ECR_REGISTRY"
export GIT_COMMIT_SHA="${GIT_COMMIT_SHA:-${DEPLOYMENT_ID:-unknown}}"
export GIT_BRANCH="${BRANCH_NAME:-master}"
export DEPLOYMENT_ENVIRONMENT="$ENVIRONMENT"

# Validate compose file syntax
echo "🧪 Validating compose file syntax..."
if docker compose -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
    echo "✅ Compose file is valid"
else
    echo "❌ Compose validation failed:"
    docker compose -f "$COMPOSE_FILE" config 2>&1
    exit 1
fi

# Pull the latest image from ECR
echo "📥 Pulling latest image from ECR..."
if [ -n "${DEPLOYMENT_IMAGE:-}" ]; then
    IMAGE_NAME="$DEPLOYMENT_IMAGE"
else
    IMAGE_NAME="$ECR_REGISTRY/$APP_IMAGE_REPOSITORY:$IMAGE_TAG"
fi

docker pull "$IMAGE_NAME"

# Tag the image for the compose file
COMPOSE_IMAGE_REFERENCE="$ECR_REGISTRY/$APP_IMAGE_REPOSITORY:$COMPOSE_IMAGE_TAG"
docker tag "$IMAGE_NAME" "$COMPOSE_IMAGE_REFERENCE"
if [ "$COMPOSE_IMAGE_TAG" != "latest" ]; then
    docker tag "$IMAGE_NAME" "$ECR_REGISTRY/$APP_IMAGE_REPOSITORY:latest"
fi

echo "📦 Deploying stack: $STACK_NAME"
echo "🐳 Using image: $IMAGE_NAME"
echo "🐳 Tagged for compose as: $COMPOSE_IMAGE_REFERENCE"

# Deploy the stack with retry logic
attempts=0
max_attempts=3

while [ $attempts -lt $max_attempts ]; do
    if docker stack deploy -c "$COMPOSE_FILE" --with-registry-auth "$STACK_NAME"; then
        echo "✅ Stack deployed successfully"
        break
    else
        attempts=$((attempts + 1))
        if [ $attempts -lt $max_attempts ]; then
            echo "⏳ Stack deploy failed, retrying in 10s (attempt $attempts/$max_attempts)..."
            sleep 10
        else
            echo "❌ Stack deploy failed after $max_attempts attempts"
            exit 1
        fi
    fi
done

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
max_wait=180
wait_time=0

while [ $wait_time -lt $max_wait ]; do
    # Check if all services have desired replicas running
    pending_services=$(docker service ls --filter "name=$STACK_NAME" --format "table {{.Name}}\t{{.Replicas}}" | grep -v "1/1" | wc -l)
    
    # Only header line should remain if all services are 1/1
    if [ $pending_services -eq 1 ]; then
        echo "✅ All services are running"
        break
    fi
    
    echo "⏳ Waiting for services to be ready... ($wait_time/$max_wait seconds)"
    docker service ls --filter "name=$STACK_NAME"
    sleep 15
    wait_time=$((wait_time + 15))
done

if [ $wait_time -ge $max_wait ]; then
    echo "⚠️ Warning: Some services may not be fully ready after $max_wait seconds"
    echo "📊 Current service status:"
    docker service ls --filter "name=$STACK_NAME"
fi

# Show final status
echo "📊 Final deployment status:"
docker service ls --filter "name=$STACK_NAME"
docker stack ps "$STACK_NAME"

echo "✅ Application Start completed successfully"