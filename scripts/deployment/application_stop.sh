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

# Check if stack exists and stop it gracefully
if docker stack ls --format "{{.Name}}" | grep -q "^${STACK_NAME}$"; then
    echo "📦 Stopping existing stack: $STACK_NAME"
    
    # Scale down services before removing stack for graceful shutdown
    for service in $(docker service ls --filter "name=${STACK_NAME}" --format "{{.Name}}"); do
        echo "🔽 Scaling down service: $service"
        docker service scale "$service=0"
    done
    
    # Wait for services to scale down
    echo "⏳ Waiting for services to scale down..."
    sleep 30
    
    # Remove the stack
    echo "🗑️ Removing stack: $STACK_NAME"
    docker stack rm "$STACK_NAME"
    
    # Wait for stack to be completely removed
    echo "⏳ Waiting for stack removal to complete..."
    while docker stack ls --format "{{.Name}}" | grep -q "^${STACK_NAME}$"; do
        echo "Waiting for stack removal..."
        sleep 10
    done
    
    echo "✅ Stack removed successfully"
else
    echo "ℹ️ No existing stack found: $STACK_NAME"
fi

# Clean up old images to save space (keep last 3 versions)
echo "🧹 Cleaning up old Docker images..."
docker image prune -f
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}" | grep "$APP_IMAGE_REPOSITORY" | tail -n +4 | awk '{print $3}' | xargs -r docker rmi || true

echo "✅ Application Stop completed successfully"