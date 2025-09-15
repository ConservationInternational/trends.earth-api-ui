#!/bin/bash

# Before Install Script for CodeDeploy
# Prepares the environment for deployment

set -e

echo "🔧 Before Install: Preparing environment for deployment"

# Get environment from deployment group name or default to production
if [[ "${DEPLOYMENT_GROUP_NAME}" == *"staging"* ]]; then
    ENVIRONMENT="staging"
    APP_PATH="/opt/trends-earth-ui-staging"
    STACK_NAME="trendsearth-ui-staging"
else
    ENVIRONMENT="production"
    APP_PATH="/opt/trends-earth-ui"
    STACK_NAME="trendsearth-ui-prod"
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

echo "✅ Before Install completed successfully"