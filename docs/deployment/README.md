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
- **Docker Image**: `${DOCKER_REGISTRY}/trendsearth-ui:staging`

## Deployment Workflow

1. **Security Group Update**: GitHub Actions runner IP is temporarily added to security group
2. **Build**: Docker image is built on the target server with git metadata
3. **Push**: Image is pushed to local Docker registry
4. **Deploy**: Docker stack deploy with rolling update
5. **Health Check**: Verification of service health and functionality
6. **Integration Tests**: Basic smoke tests
7. **Notifications**: Rollbar deployment notification
8. **Cleanup**: Remove runner IP from security group

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