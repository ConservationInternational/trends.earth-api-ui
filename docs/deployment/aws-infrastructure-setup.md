# AWS Infrastructure Setup for Trends.Earth UI Deployment

This document provides instructions for setting up the AWS infrastructure required for EC2 Docker Swarm deployment.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform (optional, for infrastructure as code)
- Access to create EC2 instances, security groups, and manage IAM

## Required AWS Resources

### 1. EC2 Instances

You need two EC2 instances:
- **Production**: For the production deployment
- **Staging**: For the staging deployment

#### Recommended Instance Configuration

**Instance Type**: t3.medium or larger
**OS**: Ubuntu 22.04 LTS
**Storage**: 20GB+ GP3 EBS volume
**Network**: Public subnet with internet gateway access

#### Security Groups

Create security groups with the following rules:

**Production Security Group** (`PROD_SECURITY_GROUP_ID`):
```
Inbound Rules:
- SSH (22): Dynamic (managed by GitHub Actions)
- HTTP (8000): 0.0.0.0/0 (or restricted to load balancer/CDN)
- HTTPS (443): 0.0.0.0/0 (if using SSL termination)

Outbound Rules:
- All traffic: 0.0.0.0/0
```

**Staging Security Group** (`STAGING_SECURITY_GROUP_ID`):
```
Inbound Rules:
- SSH (22): Dynamic (managed by GitHub Actions)  
- HTTP (8001): Your IP/Office IP ranges
- HTTPS (443): Your IP/Office IP ranges (if using SSL)

Outbound Rules:
- All traffic: 0.0.0.0/0
```

### 2. IAM User for GitHub Actions

Create an IAM user with the following policy for security group management:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:DescribeSecurityGroups"
            ],
            "Resource": "*"
        }
    ]
}
```

Store the access key ID and secret access key as GitHub secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).

## Server Setup

### 1. Initial Server Configuration

Connect to each EC2 instance and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y curl git docker.io docker-compose netcat-openbsd

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose V2
sudo apt install -y docker-compose-plugin

# Logout and login again for group changes to take effect
```

### 2. Docker Swarm Initialization

On each server, initialize Docker Swarm:

```bash
# Initialize swarm (single-node cluster)
docker swarm init

# Verify swarm status
docker node ls
```

### 3. Application Directory Setup

Create application directories:

**Production**:
```bash
sudo mkdir -p /opt/trends-earth-ui
sudo chown $USER:$USER /opt/trends-earth-ui
cd /opt/trends-earth-ui
git clone https://github.com/ConservationInternational/trends.earth-api-ui.git .
```

**Staging**:
```bash
sudo mkdir -p /opt/trends-earth-ui-staging  
sudo chown $USER:$USER /opt/trends-earth-ui-staging
cd /opt/trends-earth-ui-staging
git clone https://github.com/ConservationInternational/trends.earth-api-ui.git .
git checkout staging  # or develop
```

### 4. Docker Registry Setup

If using a private registry on the same infrastructure, set up insecure registry configuration:

```bash
sudo mkdir -p /etc/docker
echo '{"insecure-registries":["your-registry-host:5000"]}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
```

### 5. SSH Key Setup

1. Generate SSH key pairs for GitHub Actions access
2. Add public keys to `~/.ssh/authorized_keys` on each server
3. Store private keys as GitHub secrets (`PROD_SSH_KEY`, `STAGING_SSH_KEY`)

### 6. Firewall Configuration (Optional)

If using UFW:

```bash
# Production
sudo ufw allow 22
sudo ufw allow 8000
sudo ufw enable

# Staging  
sudo ufw allow 22
sudo ufw allow 8001
sudo ufw enable
```

## Load Balancer / Reverse Proxy (Optional)

For production deployments, consider setting up:

1. **Application Load Balancer (ALB)** - For SSL termination and domain routing
2. **CloudFront** - For CDN and additional SSL termination
3. **Nginx** - Local reverse proxy for advanced routing

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api-ui-health {
        proxy_pass http://localhost:8000/api-ui-health;
        access_log off;
    }
}
```

## Monitoring and Logging

Consider setting up:

1. **CloudWatch Logs** - For centralized logging
2. **CloudWatch Metrics** - For monitoring
3. **AWS Systems Manager** - For patch management
4. **Rollbar** - Application error tracking (configure `ROLLBAR_ACCESS_TOKEN`)

## Backup Strategy

1. **EBS Snapshots** - Regular automated snapshots
2. **Application Data** - If using persistent volumes
3. **Configuration Backup** - Docker compose files and environment configs

## Security Best Practices

1. **Regular Updates**: Keep OS and Docker updated
2. **Limited Access**: Restrict SSH to known IPs when possible
3. **Log Monitoring**: Monitor access logs and failed attempts  
4. **Key Rotation**: Regular rotation of SSH keys and AWS credentials
5. **Network Segmentation**: Use private subnets when possible

## Terraform Example (Optional)

For infrastructure as code, consider using Terraform. See `terraform/` directory for example configurations.

## Troubleshooting

### Common Issues

1. **Docker daemon not running**: `sudo systemctl start docker`
2. **Permission denied**: User not in docker group, logout/login required
3. **Port conflicts**: Check for existing services on ports 8000/8001
4. **Security group**: Verify GitHub Actions runner IP is allowed

### Useful Commands

```bash
# Check Docker status
sudo systemctl status docker

# View Docker logs
sudo journalctl -u docker

# Check swarm status
docker node ls

# View running services
docker service ls

# Check service logs
docker service logs trendsearth-ui-prod_ui
```