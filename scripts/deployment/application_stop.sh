#!/bin/bash

# Application Stop Script for CodeDeploy
# Gracefully stops the current deployment

set -e

echo "🛑 Application Stop: Stopping current deployment"

# Load environment variables
source /opt/deploy-env

echo "Environment: $ENVIRONMENT"
echo "Stack Name: $STACK_NAME"
APP_IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-trendsearth-api-ui}"
echo "Image Repository: $APP_IMAGE_REPOSITORY"

# Only the active swarm leader should attempt to stop or remove the stack.
echo "🔍 Checking swarm manager status..."
if ! docker info >/dev/null 2>&1; then
    echo "⚠️ Docker daemon unreachable. Skipping stop actions on this node."
    exit 0
fi

manager_status=$(docker node ls --format '{{.Self}} {{.ManagerStatus}}' 2>/dev/null | awk '$1=="true" {print $2}')
if [ -z "$manager_status" ]; then
    echo "ℹ️ This node is not part of the swarm or manager status unknown. Skipping."
    exit 0
fi

if [ "$manager_status" != "Leader" ]; then
    echo "ℹ️ Node is a swarm manager but not the leader ($manager_status). Skipping ApplicationStop."
    exit 0
fi

echo "✅ Node is the active swarm leader. Continuing stop sequence."


echo "ℹ️ Leaving stack $STACK_NAME running for zero-downtime rolling update."
echo "ℹ️ The new version will be deployed via 'docker stack deploy' in ApplicationStart."

# Clean up old images to save space (keep last 3 versions)
echo "🧹 Cleaning up old Docker images..."
docker image prune -f
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}" | grep "$APP_IMAGE_REPOSITORY" | tail -n +4 | awk '{print $3}' | xargs -r docker rmi || true

echo "✅ Application Stop completed successfully"