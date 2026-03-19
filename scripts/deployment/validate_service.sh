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
# Use 127.0.0.1 instead of localhost to avoid IPv6 resolution issues.
# Docker Swarm routing mesh listens on IPv4; curl resolving localhost to ::1
# causes connections that hang indefinitely.
if [ "$ENVIRONMENT" = "staging" ]; then
    HEALTH_URL="http://127.0.0.1:8001/api-ui-health"
    PORT=8001
else
    HEALTH_URL="http://127.0.0.1:8000/api-ui-health"
    PORT=8000
fi

echo "Health URL: $HEALTH_URL"

# Verify stack is running
echo "📊 Checking stack status..."
if ! docker stack ls --format "{{.Name}}" | grep -q "^${STACK_NAME}$"; then
    echo "❌ Stack not found: $STACK_NAME"
    exit 1
fi

# Verify services are running and capture their names
echo "🔍 Checking service status..."
service_status_output=$(docker service ls --filter "name=$STACK_NAME" --format "{{.Name}} {{.Replicas}}")

if [ -z "$service_status_output" ]; then
    echo "❌ No services found for stack: $STACK_NAME"
    docker service ls --filter "name=$STACK_NAME"
    exit 1
fi

PRIMARY_SERVICE=$(echo "$service_status_output" | head -n 1 | awk '{print $1}')

unhealthy_services=$(echo "$service_status_output" | awk '{
    split($2, counts, "/");
    if (counts[1] != counts[2]) { print $0 }
}')

if [ -n "$unhealthy_services" ]; then
    echo "❌ Some services are not running the desired replica count"
    echo "$unhealthy_services"
    echo "📊 Current service status:"
    docker service ls --filter "name=$STACK_NAME"
    exit 1
fi

service_count=$(echo "$service_status_output" | wc -l | tr -d ' ')
echo "✅ $service_count service(s) are running"

# Wait for application to be ready
echo "⏳ Waiting for application to be ready..."
max_attempts=12
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f -s --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
        echo "✅ Health check passed"
        break
    else
        attempt=$((attempt + 1))
        if [ $attempt -lt $max_attempts ]; then
            echo "⏳ Health check failed, retrying in 5s (attempt $attempt/$max_attempts)..."
            sleep 5
        else
            echo "❌ Health check failed after $max_attempts attempts"
            echo "🔍 Debugging information:"
            
            # Show service logs
            echo "📋 Service logs:"
            docker service logs "$PRIMARY_SERVICE" --tail 50 || true
            
            # Show service details
            echo "📊 Service details:"
            docker service ls --filter "name=$STACK_NAME"
            docker service ps "$PRIMARY_SERVICE" || true
            
            # Check if port is listening
            echo "🔗 Port check:"
            netstat -tulpn | grep ":$PORT " || echo "Port $PORT not listening"
            
            exit 1
        fi
    fi
done

# Get health check response for verification
echo "🩺 Health check response:"
curl -s --max-time 5 "$HEALTH_URL" | head -c 500 || echo "Failed to get response"

# Show deployment summary
echo ""
echo "📋 Deployment Summary:"
echo "  Environment: $ENVIRONMENT"
echo "  Stack: $STACK_NAME"
echo "  Health URL: $HEALTH_URL"
echo "  Status: ✅ SUCCESSFUL"

echo "✅ Validate Service completed successfully"