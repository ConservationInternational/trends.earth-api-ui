# EC2 Docker Swarm Deployment Setup

This document provides instructions for setting up the EC2 Docker Swarm deployment infrastructure and configuring the required GitHub secrets for the Trends.Earth API UI.

## Overview

The deployment uses EC2 instances with Docker Swarm for both staging and production environments. GitHub Actions connect via SSH to build Docker images locally on the servers and deploy using Docker stack commands.

## Required GitHub Secrets

The following secrets must be configured in the GitHub repository settings for the deployment workflows to function:

### AWS Credentials
- `AWS_ACCESS_KEY_ID` - AWS access key for security group management
- `AWS_SECRET_ACCESS_KEY` - AWS secret key for security group management  
- `AWS_REGION` - AWS region (default: us-east-1)

### Production Environment
- `PROD_HOST` - Production server hostname/IP
- `PROD_USERNAME` - SSH username for production server
- `PROD_SSH_KEY` - SSH private key for production server access
- `PROD_SSH_PORT` - SSH port (default: 22)
- `PROD_APP_PATH` - Path to application directory (default: /opt/trends-earth-ui)
- `PROD_SECURITY_GROUP_ID` - AWS security group ID for production server

### Staging Environment  
- `STAGING_HOST` - Staging server hostname/IP
- `STAGING_USERNAME` - SSH username for staging server
- `STAGING_SSH_KEY` - SSH private key for staging server access
- `STAGING_SSH_PORT` - SSH port (default: 22)
- `STAGING_APP_PATH` - Path to application directory (default: /opt/trends-earth-ui-staging)
- `STAGING_SECURITY_GROUP_ID` - AWS security group ID for staging server

### Docker Registry
- `DOCKER_REGISTRY` - Docker registry hostname:port (e.g., registry.example.com:5000)

### Optional
- `ROLLBAR_ACCESS_TOKEN` - Rollbar token for deployment notifications

## Architecture

### Production Environment
- **Stack Name**: `trendsearth-ui-prod`
- **Service**: `trendsearth-ui-prod_ui`
- **Port**: 8000
- **Health Endpoint**: `http://localhost:8000/api-ui-health`
- **Docker Image**: `${DOCKER_REGISTRY}/trendsearth-ui:latest`

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