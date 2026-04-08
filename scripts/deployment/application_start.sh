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

# Prefer the exact image URL provided by CI metadata; fall back to other
# known tags that we publish (branch name, compose tag, latest) but avoid
# relying on the CodeDeploy deployment ID because images are not pushed
# with that tag.
RESOLVED_IMAGE_TAG=""
IMAGE_NAME=""

if [ -n "${DEPLOYMENT_IMAGE:-}" ]; then
    IMAGE_NAME="$DEPLOYMENT_IMAGE"
    RESOLVED_IMAGE_TAG="${DEPLOYMENT_IMAGE##*:}"
elif [ -n "${IMAGE_TAG:-}" ]; then
    RESOLVED_IMAGE_TAG="$IMAGE_TAG"
    IMAGE_NAME="$ECR_REGISTRY/$APP_IMAGE_REPOSITORY:$RESOLVED_IMAGE_TAG"
else
    FALLBACK_TAG="${BRANCH_NAME:-$COMPOSE_IMAGE_TAG}"
    echo "ℹ️ No explicit image metadata provided; defaulting to tag: $FALLBACK_TAG"
    RESOLVED_IMAGE_TAG="$FALLBACK_TAG"
    IMAGE_NAME="$ECR_REGISTRY/$APP_IMAGE_REPOSITORY:$RESOLVED_IMAGE_TAG"
fi

# Last-resort fallback if everything else is empty
if [ -z "$RESOLVED_IMAGE_TAG" ]; then
    RESOLVED_IMAGE_TAG="latest"
    IMAGE_NAME="$ECR_REGISTRY/$APP_IMAGE_REPOSITORY:$RESOLVED_IMAGE_TAG"
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
export ROLLBAR_ACCESS_TOKEN="${ROLLBAR_ACCESS_TOKEN:-}"
export GOOGLE_TRANSLATE_CREDENTIALS="${GOOGLE_TRANSLATE_CREDENTIALS:-}"

# Validate compose file syntax
echo "🧪 Validating compose file syntax..."
if docker compose -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
    echo "✅ Compose file is valid"
else
    echo "⚠️ Compose validation warning (may be expected for swarm mode)"
fi

# ============================================================================
# Refresh ECR Credentials
# ============================================================================
# ECR tokens expire after 12 hours. We need fresh credentials on the node
# running docker stack deploy so --with-registry-auth can pass them to workers.

if [ -n "$ECR_REGISTRY" ]; then
    echo "🔐 Refreshing ECR credentials before stack deploy..."
    AWS_REGION="${AWS_REGION:-us-east-1}"
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_REGISTRY" || {
        echo "❌ Failed to refresh ECR credentials"
        exit 1
    }
    echo "✅ ECR credentials refreshed"
else
    echo "⚠️ ECR_REGISTRY not set, skipping ECR login"
fi

# Pull the latest image from ECR
echo "📥 Pulling latest image from ECR..."
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

# ============================================================================
# Stack Health Check - Detect and Recover from Bad State
# ============================================================================
# Docker Swarm can get into a bad state where networks exist but tasks are
# stuck or the ingress mesh has lost its iptables rules. This happens when:
#   - Previous deployment failed mid-way
#   - A container was OOM-killed and Swarm couldn't reschedule
#   - Docker daemon was restarted unexpectedly
#
# Detection: Check if stack exists but networks are missing or services are stuck
# Recovery: Remove the stack completely and redeploy fresh
# ============================================================================

echo "🔍 Checking stack health before deployment..."
STACK_EXISTS=$(docker stack ls --format "{{.Name}}" 2>/dev/null | grep -c "^${STACK_NAME}$" || echo "0")

if [ "$STACK_EXISTS" -gt 0 ]; then
    echo "📊 Stack $STACK_NAME exists, checking health..."

    # Check for services with 0 running replicas that are stuck
    stuck_services=$(docker service ls --filter "name=${STACK_NAME}" --format "{{.Name}} {{.Replicas}}" 2>/dev/null | \
        grep -E "0/[0-9]+" || echo "")

    if [ -n "$stuck_services" ]; then
        echo "⚠️ Found services with 0 running replicas:"
        echo "$stuck_services"

        # Check if tasks are stuck in New/Pending state with no node
        needs_recovery=false
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            svc_name=$(echo "$line" | awk '{print $1}')
            task_info=$(docker service ps "$svc_name" --format "{{.CurrentState}} {{.Node}}" 2>/dev/null | head -1)
            if echo "$task_info" | grep -qi "new\|pending\|rejected"; then
                echo "⚠️ Service $svc_name has stuck/rejected tasks"
                needs_recovery=true
            fi
        done <<< "$stuck_services"

        if [ "$needs_recovery" = true ]; then
            echo "🔧 Initiating stack recovery..."
            docker stack rm "$STACK_NAME" 2>/dev/null || true

            # Wait for stack resources to be fully removed
            echo "⏳ Waiting for stack resources to be cleaned up..."
            cleanup_wait=0
            while [ $cleanup_wait -lt 60 ]; do
                remaining=$(docker service ls --filter "name=${STACK_NAME}" --format "{{.Name}}" 2>/dev/null | wc -l)
                if [ "$remaining" -eq 0 ]; then
                    echo "✅ Stack resources cleaned up"
                    break
                fi
                sleep 2
                cleanup_wait=$((cleanup_wait + 2))
            done
            sleep 5
        fi
    fi
else
    echo "ℹ️ Stack $STACK_NAME does not exist, will create fresh"
fi

# Deploy the stack with retry logic
attempts=0
max_attempts=3

while [ $attempts -lt $max_attempts ]; do
    if docker stack deploy -c "$COMPOSE_FILE" --with-registry-auth --resolve-image always "$STACK_NAME"; then
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
    # Check if all services have desired replicas running (works with any replica count)
    not_ready=$(docker service ls --filter "name=$STACK_NAME" --format "{{.Replicas}}" | awk -F'/' '{ if ($1 != $2) print }' | wc -l)
    
    if [ "$not_ready" -eq 0 ]; then
        echo "✅ All services are running"
        break
    fi
    
    echo "⏳ Waiting for services to be ready... ($wait_time/$max_wait seconds)"
    docker service ls --filter "name=$STACK_NAME"
    sleep 10
    wait_time=$((wait_time + 10))
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