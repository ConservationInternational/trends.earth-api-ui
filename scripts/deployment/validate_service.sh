#!/bin/bash

# Validate Service Script for CodeDeploy
# Verifies that the deployment was successful

set -e

echo "🔍 Validate Service: Verifying deployment success"

# Load environment variables
source /opt/deploy-env

echo "Environment: $ENVIRONMENT"
echo "Stack Name: $STACK_NAME"

# Only the active swarm leader should perform validation checks. CodeDeploy may
# target multiple instances, so exit early when this node is not responsible.
echo "🔍 Checking swarm manager status..."
if ! docker info >/dev/null 2>&1; then
    echo "⚠️ Docker daemon unreachable. Skipping validation on this node."
    exit 0
fi

manager_status=$(docker node ls --format '{{.Self}} {{.ManagerStatus}}' 2>/dev/null | awk '$1=="true" {print $2}')
if [ -z "$manager_status" ]; then
    echo "ℹ️ This node is not part of the swarm or manager status unknown. Skipping."
    exit 0
fi

if [ "$manager_status" != "Leader" ]; then
    echo "ℹ️ Node is a swarm manager but not the leader ($manager_status). Skipping validation."
    exit 0
fi

echo "✅ Node is the active swarm leader. Continuing validation."

# Set health check URL based on environment
if [ "$ENVIRONMENT" = "staging" ]; then
    HEALTH_URL="http://localhost:8001/api-ui-health"
    PORT=8001
else
    HEALTH_URL="http://localhost:8000/api-ui-health"
    PORT=8000
fi

echo "Health URL: $HEALTH_URL"

# Verify stack is running
echo "📊 Checking stack status..."
if ! docker stack ls --format "{{.Name}}" | grep -q "^${STACK_NAME}$"; then
    echo "❌ Stack not found: $STACK_NAME"
    exit 1
fi

# Verify services are running
echo "🔍 Checking service status..."
service_count=$(docker service ls --filter "name=$STACK_NAME" --format "table {{.Name}}\t{{.Replicas}}" | grep -c "1/1" || echo "0")

if [ "$service_count" -eq 0 ]; then
    echo "❌ No services are running properly"
    echo "📊 Current service status:"
    docker service ls --filter "name=$STACK_NAME"
    exit 1
fi

echo "✅ $service_count service(s) are running"

# Wait for application to be ready
echo "⏳ Waiting for application to be ready..."
max_attempts=20
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f -s "$HEALTH_URL" >/dev/null 2>&1; then
        echo "✅ Health check passed"
        break
    else
        attempt=$((attempt + 1))
        if [ $attempt -lt $max_attempts ]; then
            echo "⏳ Health check failed, retrying in 15s (attempt $attempt/$max_attempts)..."
            sleep 15
        else
            echo "❌ Health check failed after $max_attempts attempts"
            echo "🔍 Debugging information:"
            
            # Show service logs
            echo "📋 Service logs:"
            docker service logs "$STACK_NAME"_ui --tail 50 || true
            
            # Show service details
            echo "📊 Service details:"
            docker service ls --filter "name=$STACK_NAME"
            docker service ps "$STACK_NAME"_ui || true
            
            # Check if port is listening
            echo "🔗 Port check:"
            netstat -tulpn | grep ":$PORT " || echo "Port $PORT not listening"
            
            exit 1
        fi
    fi
done

# Get health check response for verification
echo "🩺 Health check response:"
curl -s "$HEALTH_URL" | head -c 500 || echo "Failed to get response"

# Show deployment summary
echo ""
echo "📋 Deployment Summary:"
echo "  Environment: $ENVIRONMENT"
echo "  Stack: $STACK_NAME"
echo "  Health URL: $HEALTH_URL"
echo "  Status: ✅ SUCCESSFUL"

echo "✅ Validate Service completed successfully"