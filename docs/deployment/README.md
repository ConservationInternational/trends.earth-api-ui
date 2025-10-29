# ECR + CodeDeploy Deployment Setup

This document provides instructions for setting up the ECR + AWS CodeDeploy deployment infrastructure and configuring the required GitHub secrets for the Trends.Earth API UI.

## Overview

The deployment uses Amazon ECR (Elastic Container Registry) for container storage and AWS CodeDeploy for deployment to EC2 instances running Docker Swarm. This approach provides enhanced security by eliminating direct SSH access and leverages AWS managed services for deployment automation.

## Required GitHub Secrets

The following secrets must be configured in the GitHub repository settings for the deployment workflows to function:

### AWS Credentials
- `AWS_ACCESS_KEY_ID` - AWS access key for ECR, CodeDeploy, and S3 access
- `AWS_SECRET_ACCESS_KEY` - AWS secret key for ECR, CodeDeploy, and S3 access  
- `AWS_REGION` - AWS region (default: us-east-1)

### CodeDeploy Configuration
- `CODEDEPLOY_S3_BUCKET` - S3 bucket for CodeDeploy deployment artifacts

### Optional
- `ROLLBAR_ACCESS_TOKEN` - Rollbar token for deployment notifications

## Architecture

### Production Environment
- **Stack Name**: `trendsearth-ui-prod`
- **Service**: `trendsearth-ui-prod_ui`
- **Port**: 8000
- **Health Endpoint**: `http://localhost:8000/api-ui-health`
- **Docker Image**: ECR registry with commit-specific tags

### Staging Environment
- **Stack Name**: `trendsearth-ui-staging` 
- **Service**: `trendsearth-ui-staging_ui`
- **Port**: 8001 (external), 8000 (internal)
- **Health Endpoint**: `http://localhost:8001/api-ui-health`
- **Docker Image**: ECR registry with branch-specific tags

## ECR Integration

The Docker Compose files use ECR images through environment variable substitution:

- **Image Format**: `${DOCKER_REGISTRY}/trendsearth-ui:latest`
- **ECR Authentication**: Handled by CodeDeploy scripts in `scripts/deployment/before_install.sh`
- **Registry Resolution**: `DOCKER_REGISTRY` environment variable is set to ECR registry URL during deployment
- **Fallback Registry**: Falls back to `127.0.0.1:5000` for local development

### How ECR Access Works
1. **Authentication**: `before_install.sh` runs `aws ecr get-login-password` to authenticate Docker with ECR
2. **Registry Configuration**: `application_start.sh` sets `DOCKER_REGISTRY` to ECR URL format: `{account-id}.dkr.ecr.{region}.amazonaws.com`
3. **Image Resolution**: Docker Compose resolves `${DOCKER_REGISTRY}/trendsearth-ui:latest` to the ECR image
4. **Registry Auth**: Docker Swarm uses `--with-registry-auth` to pass ECR credentials to all nodes

## Deployment Workflow

1. **Build & Push**: Docker image is built in GitHub Actions and pushed to Amazon ECR
2. **CodeDeploy Bundle**: Deployment artifacts (appspec.yml, scripts, compose files) are packaged and uploaded to S3
3. **CodeDeploy Deployment**: AWS CodeDeploy orchestrates deployment to EC2 instances
4. **ECR Authentication**: EC2 instances authenticate with ECR using IAM roles
5. **Docker Swarm Update**: New image is pulled from ECR and deployed via Docker Swarm rolling update
6. **Health Check**: Verification of service health via `/api-ui-health` endpoint
7. **Notifications**: Rollbar deployment notification via CodeDeploy hooks

## Rollback Process

The rollback workflow supports two methods:

1. **Automatic Rollback**: Uses Docker Swarm's built-in rollback to previous image
2. **Commit Rollback**: Builds and deploys from a specific Git commit SHA

## Next Steps

1. Set up AWS infrastructure using the provided scripts
2. Configure GitHub secrets using the setup script
3. Verify deployment workflows work correctly
4. Monitor application health and performance

## Related Files

- `docker-compose.prod.yml` - Production stack configuration
- `docker-compose.staging.yml` - Staging stack configuration  
- `.github/workflows/deploy-production.yml` - Production deployment workflow
- `.github/workflows/deploy-staging.yml` - Staging deployment workflow
- `.github/workflows/rollback-production.yml` - Production rollback workflow
- `docs/deployment/aws-infrastructure-setup.md` - AWS setup instructions
- `scripts/setup-github-secrets.sh` - GitHub secrets configuration script