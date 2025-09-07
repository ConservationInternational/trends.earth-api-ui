#!/bin/bash

# EC2 Instance Setup Guide for Trends.Earth UI Deployment
# This script provides guidance and examples for EC2 instance setup
# Note: EC2 instance creation is typically done through AWS Console or Terraform

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Default values
DEFAULT_INSTANCE_PROFILE="TrendsEarthUIInstanceProfile"
DEFAULT_KEY_NAME=""
DEFAULT_SECURITY_GROUP=""

main() {
    echo -e "${BLUE}💻 EC2 Instance Setup Guide for Trends.Earth UI${NC}"
    echo "================================================"
    echo ""
    
    # Check prerequisites
    check_aws_cli || exit 1
    
    local instance_profile
    local key_name
    local security_group_prod
    local security_group_staging
    local region
    local account_id
    
    # Get AWS account info
    account_id=$(get_aws_account_id)
    region=$(get_aws_region)
    
    # Get configuration
    log_step "Getting configuration..."
    prompt_with_default "Enter IAM instance profile name" "$DEFAULT_INSTANCE_PROFILE" instance_profile
    prompt_with_default "Enter EC2 key pair name (for SSH access)" "$DEFAULT_KEY_NAME" key_name
    
    echo ""
    log_info "This script will help you:"
    log_info "1. Create security groups for production and staging"
    log_info "2. Generate user data script for instance initialization"
    log_info "3. Provide commands for instance creation"
    log_info "4. Show instance tagging commands"
    echo ""
    
    if confirm "Do you want to create security groups?"; then
        create_security_groups
        echo ""
    fi
    
    if confirm "Do you want to generate user data script?"; then
        generate_user_data_script
        echo ""
    fi
    
    if confirm "Do you want to see instance creation commands?"; then
        show_instance_creation_commands "$instance_profile" "$key_name"
        echo ""
    fi
    
    show_tagging_commands
    show_verification_commands
    
    echo ""
    log_success "EC2 setup guide completed!"
    echo ""
    log_warning "Important reminders:"
    log_info "1. Ensure instances have internet access for downloading packages"
    log_info "2. Attach the IAM instance profile to all instances"
    log_info "3. Tag instances appropriately for CodeDeploy discovery"
    log_info "4. Verify CodeDeploy agent is running after instance launch"
    log_info "5. Test Docker and Docker Swarm functionality"
}

create_security_groups() {
    log_step "Creating security groups..."
    
    local prod_sg_name="trendsearth-ui-prod-sg"
    local staging_sg_name="trendsearth-ui-staging-sg"
    
    # Production security group
    log_info "Creating production security group..."
    
    local prod_sg_id
    if prod_sg_id=$(aws ec2 create-security-group \
        --group-name "$prod_sg_name" \
        --description "Security group for Trends.Earth UI Production" \
        --query 'GroupId' \
        --output text 2>/dev/null); then
        log_success "Production security group created: $prod_sg_id"
        
        # Add rules for production (port 8000)
        aws ec2 authorize-security-group-ingress \
            --group-id "$prod_sg_id" \
            --protocol tcp \
            --port 8000 \
            --cidr 0.0.0.0/0 &>/dev/null
        
        # Add SSH access if key pair was specified
        if [ -n "$key_name" ]; then
            aws ec2 authorize-security-group-ingress \
                --group-id "$prod_sg_id" \
                --protocol tcp \
                --port 22 \
                --cidr 0.0.0.0/0 &>/dev/null
        fi
        
        log_success "Production security group rules added"
    else
        log_warning "Production security group may already exist"
    fi
    
    # Staging security group
    log_info "Creating staging security group..."
    
    local staging_sg_id
    if staging_sg_id=$(aws ec2 create-security-group \
        --group-name "$staging_sg_name" \
        --description "Security group for Trends.Earth UI Staging" \
        --query 'GroupId' \
        --output text 2>/dev/null); then
        log_success "Staging security group created: $staging_sg_id"
        
        # Add rules for staging (port 8001) - restrict to your IP
        echo -n -e "${YELLOW}Enter your IP address or CIDR for staging access (e.g., 203.0.113.1/32): ${NC}"
        local staging_cidr
        read staging_cidr
        
        if [ -n "$staging_cidr" ]; then
            aws ec2 authorize-security-group-ingress \
                --group-id "$staging_sg_id" \
                --protocol tcp \
                --port 8001 \
                --cidr "$staging_cidr" &>/dev/null
        else
            log_warning "No CIDR provided, staging will be accessible from anywhere"
            aws ec2 authorize-security-group-ingress \
                --group-id "$staging_sg_id" \
                --protocol tcp \
                --port 8001 \
                --cidr 0.0.0.0/0 &>/dev/null
        fi
        
        # Add SSH access if key pair was specified
        if [ -n "$key_name" ]; then
            aws ec2 authorize-security-group-ingress \
                --group-id "$staging_sg_id" \
                --protocol tcp \
                --port 22 \
                --cidr 0.0.0.0/0 &>/dev/null
        fi
        
        log_success "Staging security group rules added"
    else
        log_warning "Staging security group may already exist"
    fi
    
    echo ""
    log_info "Security group details:"
    log_info "  Production: $prod_sg_name ($prod_sg_id) - Port 8000 open to world"
    log_info "  Staging: $staging_sg_name ($staging_sg_id) - Port 8001 restricted"
}

generate_user_data_script() {
    log_step "Generating user data script..."
    
    local user_data_file="/tmp/ec2-user-data.sh"
    
    cat > "$user_data_file" <<'EOF'
#!/bin/bash

# EC2 User Data Script for Trends.Earth UI
# This script sets up Docker, Docker Swarm, and CodeDeploy agent

set -e

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a /var/log/trends-earth-setup.log
}

log "Starting Trends.Earth UI instance setup..."

# Update system
log "Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker
log "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Start Docker service
systemctl enable docker
systemctl start docker

# Initialize Docker Swarm
log "Initializing Docker Swarm..."
docker swarm init || log "Docker Swarm may already be initialized"

# Install CodeDeploy agent
log "Installing CodeDeploy agent..."
apt-get install -y ruby wget

cd /home/ubuntu
wget https://aws-codedeploy-us-east-1.s3.us-east-1.amazonaws.com/latest/install
chmod +x ./install
./install auto

# Install AWS CLI v2
log "Installing AWS CLI v2..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
apt-get install -y unzip
unzip awscliv2.zip
./aws/install

# Install CloudWatch agent (optional)
log "Installing CloudWatch agent..."
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb

# Start CodeDeploy agent
log "Starting CodeDeploy agent..."
systemctl enable codedeploy-agent
systemctl start codedeploy-agent

# Create application directory
log "Creating application directory..."
mkdir -p /opt/trendsearth-ui
chown ubuntu:ubuntu /opt/trendsearth-ui

# Set up log rotation
log "Setting up log rotation..."
cat > /etc/logrotate.d/trendsearth-ui <<LOGROTATE
/var/log/trends-earth-*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 ubuntu ubuntu
}
LOGROTATE

log "Instance setup completed successfully!"
log "CodeDeploy agent status: $(systemctl is-active codedeploy-agent)"
log "Docker status: $(systemctl is-active docker)"

# Verify installations
docker --version
aws --version
ruby --version

log "Setup script finished. Check /var/log/trends-earth-setup.log for details."
EOF
    
    log_success "User data script generated: $user_data_file"
    echo ""
    log_info "User data script features:"
    log_info "  ✅ System updates"
    log_info "  ✅ Docker installation and Swarm initialization"
    log_info "  ✅ CodeDeploy agent installation"
    log_info "  ✅ AWS CLI v2 installation"
    log_info "  ✅ CloudWatch agent installation"
    log_info "  ✅ Application directory setup"
    log_info "  ✅ Log rotation configuration"
    echo ""
    log_info "To use this script, copy the contents to the User Data field when launching EC2 instances."
}

show_instance_creation_commands() {
    local instance_profile="$1"
    local key_name="$2"
    
    log_step "Instance creation commands..."
    
    echo ""
    log_info "Production instance creation:"
    echo "aws ec2 run-instances \\"
    echo "    --image-id ami-0c02fb55956c7d316 \\"  # Ubuntu 22.04 LTS in us-east-1
    echo "    --instance-type t3.medium \\"
    echo "    --key-name $key_name \\"
    echo "    --security-group-ids sg-PRODUCTION-SECURITY-GROUP-ID \\"
    echo "    --iam-instance-profile Name=$instance_profile \\"
    echo "    --user-data file:///tmp/ec2-user-data.sh \\"
    echo "    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=TrendsEarth-UI-Production},{Key=Environment,Value=Production},{Key=Application,Value=trendsearth-ui}]' \\"
    echo "    --block-device-mappings '[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":20,\"VolumeType\":\"gp3\"}}]'"
    
    echo ""
    log_info "Staging instance creation:"
    echo "aws ec2 run-instances \\"
    echo "    --image-id ami-0c02fb55956c7d316 \\"  # Ubuntu 22.04 LTS in us-east-1
    echo "    --instance-type t3.medium \\"
    echo "    --key-name $key_name \\"
    echo "    --security-group-ids sg-STAGING-SECURITY-GROUP-ID \\"
    echo "    --iam-instance-profile Name=$instance_profile \\"
    echo "    --user-data file:///tmp/ec2-user-data.sh \\"
    echo "    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=TrendsEarth-UI-Staging},{Key=Environment,Value=Staging},{Key=Application,Value=trendsearth-ui}]' \\"
    echo "    --block-device-mappings '[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":20,\"VolumeType\":\"gp3\"}}]'"
    
    echo ""
    log_warning "Replace the following placeholders:"
    log_info "  - ami-0c02fb55956c7d316: Use appropriate AMI ID for your region"
    log_info "  - sg-PRODUCTION-SECURITY-GROUP-ID: Use actual security group ID"
    log_info "  - sg-STAGING-SECURITY-GROUP-ID: Use actual security group ID"
    log_info "  - $key_name: Use your actual key pair name"
}

show_tagging_commands() {
    log_step "Instance tagging commands..."
    
    echo ""
    log_info "After instance creation, tag them for CodeDeploy discovery:"
    echo ""
    log_info "For Production instance:"
    echo "aws ec2 create-tags --resources i-PRODUCTION-INSTANCE-ID --tags \\"
    echo "    Key=Environment,Value=Production \\"
    echo "    Key=Application,Value=trendsearth-ui"
    echo ""
    log_info "For Staging instance:"
    echo "aws ec2 create-tags --resources i-STAGING-INSTANCE-ID --tags \\"
    echo "    Key=Environment,Value=Staging \\"
    echo "    Key=Application,Value=trendsearth-ui"
    
    echo ""
    log_info "To find your instance IDs:"
    echo "aws ec2 describe-instances --filters \"Name=tag:Name,Values=TrendsEarth-UI-Production\" --query 'Reservations[*].Instances[*].InstanceId' --output text"
}

show_verification_commands() {
    log_step "Verification commands..."
    
    echo ""
    log_info "After instance launch, verify the setup:"
    echo ""
    log_info "1. Check instance status:"
    echo "   aws ec2 describe-instances --instance-ids i-INSTANCE-ID"
    echo ""
    log_info "2. SSH to instance and verify services:"
    echo "   ssh ubuntu@INSTANCE-PUBLIC-IP"
    echo "   sudo systemctl status codedeploy-agent"
    echo "   sudo systemctl status docker"
    echo "   docker node ls"
    echo ""
    log_info "3. Check CodeDeploy agent logs:"
    echo "   sudo tail -f /var/log/aws/codedeploy-agent/codedeploy-agent.log"
    echo ""
    log_info "4. Test ECR authentication:"
    echo "   aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi