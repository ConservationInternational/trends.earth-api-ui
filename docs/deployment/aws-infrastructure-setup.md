# AWS Infrastructure Setup for ECR + CodeDeploy Deployment

This document provides instructions for setting up the AWS infrastructure required for ECR + CodeDeploy deployment of the Trends.Earth API UI.

## Quick Start with Automated Scripts

🚀 **Recommended**: Use the automated setup scripts for a guided, validated setup experience.

### Interactive Setup (Recommended)
```bash
./scripts/setup-aws-infrastructure.sh
```

### Quick Setup with Defaults
```bash
./scripts/setup-aws-infrastructure.sh --quick
```

### Check Existing Infrastructure
```bash
./scripts/setup-aws-infrastructure.sh --check
```

### Individual Component Setup
You can also set up individual components:

```bash
# ECR repository only
./scripts/aws-setup/setup-ecr.sh

# S3 bucket for CodeDeploy artifacts
./scripts/aws-setup/setup-s3.sh

# IAM roles and policies
./scripts/aws-setup/setup-iam.sh

# CodeDeploy application and deployment groups
./scripts/aws-setup/setup-codedeploy.sh

# EC2 instance setup guide
./scripts/aws-setup/setup-ec2.sh
```

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform (optional, for infrastructure as code)
- Access to create ECR repositories, CodeDeploy applications, EC2 instances, S3 buckets, and manage IAM

## Script Features

The automated setup scripts provide:

- ✅ **Error handling** - Graceful error handling with clear error messages
- ✅ **Idempotent operations** - Safe to run multiple times
- ✅ **Resource checking** - Detects existing resources and offers to update them
- ✅ **Configuration prompts** - Interactive prompts with sensible defaults
- ✅ **Progress tracking** - Clear progress indicators and success/failure feedback
- ✅ **Comprehensive output** - Detailed information about created resources
- ✅ **Next steps guidance** - Clear instructions for post-setup tasks

## Manual Setup Instructions

If you prefer to set up the infrastructure manually or need to understand the individual steps, the following sections provide detailed AWS CLI commands for each component.

> **Note**: The automated scripts above handle all these steps with proper validation and error handling. Manual setup is provided for reference and customization purposes.

## Required AWS Resources

### 1. Amazon ECR Repository

Create an ECR repository to store Docker images:

```bash
# Create ECR repository
aws ecr create-repository \
    --repository-name trendsearth-api-ui \
    --region us-east-1

# Set lifecycle policy to cleanup old images
aws ecr put-lifecycle-policy \
    --repository-name trendsearth-api-ui \
    --lifecycle-policy-text '{
        "rules": [
            {
                "rulePriority": 1,
                "description": "Keep last 10 images",
                "selection": {
                    "tagStatus": "any",
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }'
```

### 2. S3 Bucket for CodeDeploy Artifacts

Create an S3 bucket to store deployment bundles:

```bash
# Create S3 bucket for deployment artifacts
aws s3 mb s3://your-codedeploy-artifacts-bucket

# Set lifecycle policy to cleanup old artifacts
aws s3api put-bucket-lifecycle-configuration \
    --bucket your-codedeploy-artifacts-bucket \
    --lifecycle-configuration '{
        "Rules": [
            {
                "ID": "DeleteOldDeployments",
                "Status": "Enabled",
                "Filter": {"Prefix": "deployments/"},
                "Expiration": {"Days": 30}
            }
        ]
    }'
```

### 3. IAM Roles and Policies

#### CodeDeploy Service Role

```bash
# Create trust policy for CodeDeploy
cat > codedeploy-trust-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "codedeploy.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create CodeDeploy service role
aws iam create-role \
    --role-name CodeDeployServiceRole \
    --assume-role-policy-document file://codedeploy-trust-policy.json

# Attach the managed policy for CodeDeploy
aws iam attach-role-policy \
    --role-name CodeDeployServiceRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole
```

#### EC2 Instance Role for CodeDeploy Agent

```bash
# Create trust policy for EC2
cat > ec2-trust-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create EC2 instance role
aws iam create-role \
    --role-name TrendsEarthAPIUIInstanceRole \
    --assume-role-policy-document file://ec2-trust-policy.json

# Create policy for ECR and S3 access
cat > ec2-deployment-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-codedeploy-artifacts-bucket",
                "arn:aws:s3:::your-codedeploy-artifacts-bucket/*"
            ]
        }
    ]
}
EOF

# Attach policies to EC2 role
aws iam put-role-policy \
    --role-name TrendsEarthAPIUIInstanceRole \
    --policy-name ECRAndS3Access \
    --policy-document file://ec2-deployment-policy.json

aws iam attach-role-policy \
    --role-name TrendsEarthAPIUIInstanceRole \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy

aws iam attach-role-policy \
    --role-name TrendsEarthAPIUIInstanceRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforAWSCodeDeploy

# Create instance profile
aws iam create-instance-profile \
    --instance-profile-name TrendsEarthAPIUIInstanceProfile

aws iam add-role-to-instance-profile \
    --instance-profile-name TrendsEarthAPIUIInstanceProfile \
    --role-name TrendsEarthAPIUIInstanceRole
```

### 4. EC2 Instances

#### Instance Configuration

**Instance Type**: t3.medium or larger  
**OS**: Ubuntu 22.04 LTS  
**Storage**: 20GB+ GP3 EBS volume  
**Network**: Public subnet with internet gateway access  
**IAM Instance Profile**: TrendsEarthAPIUIInstanceProfile

#### Security Groups

Create security groups for the instances:

```bash
# Production Security Group
aws ec2 create-security-group \
    --group-name trendsearth-api-ui-prod-sg \
    --description "Security group for Trends.Earth UI Production"

# Add rules for production
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0

# Staging Security Group  
aws ec2 create-security-group \
    --group-name trendsearth-api-ui-staging-sg \
    --description "Security group for Trends.Earth UI Staging"

# Add rules for staging (restrict to your IP ranges)
aws ec2 authorize-security-group-ingress \
    --group-id sg-yyyyyyyyy \
    --protocol tcp \
    --port 8001 \
    --cidr YOUR_IP_RANGE/32
```

#### Instance User Data Script

```bash
#!/bin/bash
# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Initialize Docker Swarm
docker swarm init

# Install CodeDeploy agent
apt-get install -y ruby wget
cd /home/ubuntu
wget https://aws-codedeploy-us-east-1.s3.us-east-1.amazonaws.com/latest/install
chmod +x ./install
./install auto

# Install AWS CLI
apt-get install -y awscli

# Start CodeDeploy agent
service codedeploy-agent start
```

### 5. CodeDeploy Application and Deployment Groups

```bash
# Create CodeDeploy application
aws deploy create-application \
    --application-name trendsearth-api-ui \
    --compute-platform Server

# Create production deployment group
aws deploy create-deployment-group \
    --application-name trendsearth-api-ui \
    --deployment-group-name production \
    --service-role-arn arn:aws:iam::ACCOUNT_ID:role/CodeDeployServiceRole \
    --ec2-tag-set "ec2TagSetList=[[{Key=Application,Value=trendsearth-api-ui,Type=KEY_AND_VALUE},{Key=CodeDeployGroupProduction,Value=true,Type=KEY_AND_VALUE}]]" \
    --deployment-config-name CodeDeployDefault.AllAtOnce \
    --auto-rollback-configuration enabled=true,events=DEPLOYMENT_FAILURE,DEPLOYMENT_STOP_ON_ALARM

# Create staging deployment group
aws deploy create-deployment-group \
    --application-name trendsearth-api-ui \
    --deployment-group-name staging \
    --service-role-arn arn:aws:iam::ACCOUNT_ID:role/CodeDeployServiceRole \
    --ec2-tag-set "ec2TagSetList=[[{Key=Application,Value=trendsearth-api-ui,Type=KEY_AND_VALUE},{Key=CodeDeployGroupStaging,Value=true,Type=KEY_AND_VALUE}]]" \
    --deployment-config-name CodeDeployDefault.AllAtOnce \
    --auto-rollback-configuration enabled=true,events=DEPLOYMENT_FAILURE,DEPLOYMENT_STOP_ON_ALARM
```

### 6. Instance Tags

Tag your EC2 instances so CodeDeploy can identify them:

```bash
# Production deployment tag
aws ec2 create-tags \
    --resources i-1234567890abcdef0 \
    --tags Key=Application,Value=trendsearth-api-ui Key=CodeDeployGroupProduction,Value=true

# Staging deployment tag  
aws ec2 create-tags \
    --resources i-abcdef1234567890 \
    --tags Key=Application,Value=trendsearth-api-ui Key=CodeDeployGroupStaging,Value=true

# Single instance hosting both deployment groups
aws ec2 create-tags \
    --resources i-abcdef1234567890 \
    --tags Key=CodeDeployGroupProduction,Value=true Key=CodeDeployGroupStaging,Value=true
```

## Setup Process Overview

The automated setup scripts handle the following components in order:

1. **ECR Repository** (`setup-ecr.sh`)
    - Creates the `trendsearth-api-ui` repository
   - Sets up lifecycle policies for image cleanup
   - Configures appropriate permissions

2. **S3 Bucket** (`setup-s3.sh`)
   - Creates bucket for CodeDeploy deployment artifacts
   - Enables versioning and blocks public access
   - Sets up lifecycle policies for artifact cleanup

3. **IAM Roles** (`setup-iam.sh`)
   - Creates CodeDeploy service role with required policies
   - Creates EC2 instance role with ECR, S3, and logging permissions
   - Sets up instance profile for EC2 instances

4. **CodeDeploy Application** (`setup-codedeploy.sh`)
   - Creates CodeDeploy application
   - Sets up production and staging deployment groups
   - Configures auto-rollback policies

5. **EC2 Setup Guide** (`setup-ec2.sh`)
   - Provides guidance for EC2 instance creation
   - Generates user data scripts for instance initialization
   - Shows commands for security group creation and instance tagging

## GitHub Secrets Configuration

After setting up the AWS infrastructure, configure GitHub secrets:

```bash
# Set up GitHub secrets for deployment
./scripts/setup-github-secrets.sh
```

This script will prompt for and configure:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `CODEDEPLOY_S3_BUCKET`
- `ROLLBAR_ACCESS_TOKEN` (optional)

## Verification Commands

After setup, verify your infrastructure:

```bash
# Check all components
./scripts/setup-aws-infrastructure.sh --check

# Verify specific resources
aws ecr describe-repositories --repository-names trendsearth-api-ui
aws s3api head-bucket --bucket your-bucket-name
aws deploy get-application --application-name trendsearth-api-ui
aws iam get-role --role-name TrendsEarthAPIUICodeDeployRole
```

## Benefits of This Architecture

1. **Enhanced Security** - No SSH keys or direct server access required
2. **Managed Services** - Leverages AWS managed services for reliability
3. **Audit Trail** - Complete deployment history and logging
4. **Rollback Capabilities** - Built-in rollback support
5. **Scalability** - Easy to add more instances to deployment groups
6. **Monitoring** - Integrated with CloudWatch for monitoring and alerting

## Troubleshooting

### Common Issues

**Script Permissions**
```bash
# If scripts are not executable
chmod +x scripts/setup-aws-infrastructure.sh scripts/aws-setup/*.sh
```

**AWS CLI Configuration**
```bash
# Verify AWS CLI is configured
aws sts get-caller-identity
aws configure list
```

**Resource Already Exists**
- Scripts will detect existing resources and offer to update them
- Use `--check` flag to see what already exists before running setup

### Detailed Troubleshooting

- **CodeDeploy Agent Issues**: Check `/var/log/aws/codedeploy-agent/` logs
- **ECR Authentication**: Verify IAM permissions for ECR access
- **S3 Access**: Confirm bucket policies and IAM permissions
- **Docker Issues**: Check Docker daemon status and swarm mode
- **Health Check Failures**: Review application logs and health endpoint responses

For more detailed troubleshooting, refer to the AWS CodeDeploy and ECR documentation.