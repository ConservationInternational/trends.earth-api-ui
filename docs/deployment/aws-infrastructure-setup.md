# AWS Infrastructure Setup for ECR + CodeDeploy Deployment

This document provides instructions for setting up the AWS infrastructure required for ECR + CodeDeploy deployment of the Trends.Earth API UI.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform (optional, for infrastructure as code)
- Access to create ECR repositories, CodeDeploy applications, EC2 instances, S3 buckets, and manage IAM

## Required AWS Resources

### 1. Amazon ECR Repository

Create an ECR repository to store Docker images:

```bash
# Create ECR repository
aws ecr create-repository \
    --repository-name trendsearth-ui \
    --region us-east-1

# Set lifecycle policy to cleanup old images
aws ecr put-lifecycle-policy \
    --repository-name trendsearth-ui \
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
    --role-name TrendsEarthUIInstanceRole \
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
    --role-name TrendsEarthUIInstanceRole \
    --policy-name ECRAndS3Access \
    --policy-document file://ec2-deployment-policy.json

aws iam attach-role-policy \
    --role-name TrendsEarthUIInstanceRole \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy

aws iam attach-role-policy \
    --role-name TrendsEarthUIInstanceRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforAWSCodeDeploy

# Create instance profile
aws iam create-instance-profile \
    --instance-profile-name TrendsEarthUIInstanceProfile

aws iam add-role-to-instance-profile \
    --instance-profile-name TrendsEarthUIInstanceProfile \
    --role-name TrendsEarthUIInstanceRole
```

### 4. EC2 Instances

#### Instance Configuration

**Instance Type**: t3.medium or larger  
**OS**: Ubuntu 22.04 LTS  
**Storage**: 20GB+ GP3 EBS volume  
**Network**: Public subnet with internet gateway access  
**IAM Instance Profile**: TrendsEarthUIInstanceProfile

#### Security Groups

Create security groups for the instances:

```bash
# Production Security Group
aws ec2 create-security-group \
    --group-name trendsearth-ui-prod-sg \
    --description "Security group for Trends.Earth UI Production"

# Add rules for production
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0

# Staging Security Group  
aws ec2 create-security-group \
    --group-name trendsearth-ui-staging-sg \
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
    --application-name trendsearth-ui \
    --compute-platform Server

# Create production deployment group
aws deploy create-deployment-group \
    --application-name trendsearth-ui \
    --deployment-group-name production \
    --service-role-arn arn:aws:iam::ACCOUNT_ID:role/CodeDeployServiceRole \
    --ec2-tag-filters Key=Environment,Value=Production,Type=KEY_AND_VALUE \
    --deployment-config-name CodeDeployDefault.AllAtOneTime \
    --auto-rollback-configuration enabled=true,events=DEPLOYMENT_FAILURE

# Create staging deployment group
aws deploy create-deployment-group \
    --application-name trendsearth-ui \
    --deployment-group-name staging \
    --service-role-arn arn:aws:iam::ACCOUNT_ID:role/CodeDeployServiceRole \
    --ec2-tag-filters Key=Environment,Value=Staging,Type=KEY_AND_VALUE \
    --deployment-config-name CodeDeployDefault.AllAtOneTime \
    --auto-rollback-configuration enabled=true,events=DEPLOYMENT_FAILURE
```

### 6. Instance Tags

Tag your EC2 instances so CodeDeploy can identify them:

```bash
# Production instance
aws ec2 create-tags \
    --resources i-1234567890abcdef0 \
    --tags Key=Environment,Value=Production Key=Application,Value=trendsearth-ui

# Staging instance  
aws ec2 create-tags \
    --resources i-abcdef1234567890 \
    --tags Key=Environment,Value=Staging Key=Application,Value=trendsearth-ui
```

## Required GitHub Secrets

After setting up the infrastructure, configure these GitHub secrets:

- `AWS_ACCESS_KEY_ID` - AWS access key with ECR, CodeDeploy, and S3 permissions
- `AWS_SECRET_ACCESS_KEY` - Corresponding secret key  
- `AWS_REGION` - AWS region (e.g., us-east-1)
- `CODEDEPLOY_S3_BUCKET` - S3 bucket name for deployment artifacts
- `ROLLBAR_ACCESS_TOKEN` - (Optional) Rollbar access token

## Verification

1. **ECR Repository**: Verify repository exists and has appropriate permissions
2. **S3 Bucket**: Confirm bucket exists and is accessible
3. **IAM Roles**: Verify roles have correct policies attached
4. **EC2 Instances**: Check instances are running with correct tags and instance profiles
5. **CodeDeploy**: Verify application and deployment groups are created
6. **CodeDeploy Agent**: Confirm agent is running on all instances

```bash
# Check CodeDeploy agent status on instances
ssh ubuntu@instance-ip 'sudo service codedeploy-agent status'

# Verify ECR repository
aws ecr describe-repositories --repository-names trendsearth-ui

# Verify CodeDeploy application
aws deploy get-application --application-name trendsearth-ui
```

## Benefits of This Architecture

1. **Enhanced Security** - No SSH keys or direct server access required
2. **Managed Services** - Leverages AWS managed services for reliability
3. **Audit Trail** - Complete deployment history and logging
4. **Rollback Capabilities** - Built-in rollback support
5. **Scalability** - Easy to add more instances to deployment groups
6. **Monitoring** - Integrated with CloudWatch for monitoring and alerting

## Troubleshooting

- **CodeDeploy Agent Issues**: Check `/var/log/aws/codedeploy-agent/` logs
- **ECR Authentication**: Verify IAM permissions for ECR access
- **S3 Access**: Confirm bucket policies and IAM permissions
- **Docker Issues**: Check Docker daemon status and swarm mode
- **Health Check Failures**: Review application logs and health endpoint responses

For more detailed troubleshooting, refer to the AWS CodeDeploy and ECR documentation.