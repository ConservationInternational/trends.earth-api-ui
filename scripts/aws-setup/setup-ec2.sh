#!/bin/bash

# EC2 Instance Setup Guide for Trends.Earth UI Deployment
# This script provides guidance and examples for EC2 instance setup
# Note: EC2 instance creation is typically done through AWS Console or Terraform

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Default values
DEFAULT_INSTANCE_PROFILE="TrendsEarthAPIUIInstanceProfile"
DEFAULT_KEY_NAME=""
DEFAULT_SECURITY_GROUP=""
DEFAULT_S3_BUCKET="trendsearth-api-ui-codedeploy-artifacts"
DEFAULT_APP_TAG_VALUE="trendsearth-api-ui"
PRODUCTION_TAG_KEY="CodeDeployGroupProduction"
STAGING_TAG_KEY="CodeDeployGroupStaging"

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
    
    echo ""
    if confirm "Configure existing Docker Swarm instance(s) for CodeDeploy (skip new instance guidance)?"; then
        configure_existing_swarm "$instance_profile"
        echo ""
        log_success "Existing Docker Swarm configuration steps completed"
        return
    fi

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
    
    local prod_sg_name="trendsearth-api-ui-prod-sg"
    local staging_sg_name="trendsearth-api-ui-staging-sg"
    
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

configure_existing_swarm() {
    local instance_profile="$1"

    log_step "Configuring existing Docker Swarm instance(s) for CodeDeploy"

    echo -n -e "${YELLOW}Enter EC2 instance IDs of swarm managers to configure (comma-separated): ${NC}"
    local instance_ids_raw
    read instance_ids_raw

    if [ -z "$instance_ids_raw" ]; then
        log_error "At least one instance ID is required"
        exit 1
    fi

    echo -n -e "${YELLOW}Enter CIDR allowed to access staging on port 8001 [0.0.0.0/0]: ${NC}"
    local staging_cidr
    read staging_cidr
    staging_cidr=${staging_cidr:-0.0.0.0/0}

    local s3_bucket
    prompt_with_default "Enter S3 bucket name for deployment artifacts" "$DEFAULT_S3_BUCKET" s3_bucket

    local account_id region
    account_id=$(get_aws_account_id)
    region=$(get_aws_region)

    for raw_id in ${instance_ids_raw//,/ }; do
        local instance_id
        instance_id=$(echo "$raw_id" | xargs)
        if [ -z "$instance_id" ]; then
            continue
        fi

        if ! aws ec2 describe-instances --instance-ids "$instance_id" \
            --query 'Reservations[0].Instances[0].InstanceId' --output text &>/dev/null; then
            log_error "Instance '$instance_id' not found or not accessible"
            exit 1
        fi

        log_info "Configuring instance: $instance_id"

        aws ec2 describe-instances --instance-ids "$instance_id" \
            --query 'Reservations[0].Instances[0].{Name:Tags[?Key==`Name`].Value|[0],PublicIp:PublicIpAddress,PrivateIp:PrivateIpAddress}' \
            --output table

        local sg_table
        sg_table=$(aws ec2 describe-instances --instance-ids "$instance_id" \
            --query 'Reservations[0].Instances[0].SecurityGroups[*].[GroupId,GroupName]' --output table)

        echo "$sg_table"

        local default_sg
        default_sg=$(aws ec2 describe-instances --instance-ids "$instance_id" \
            --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

        echo -n -e "${YELLOW}Enter security group ID to update for application ports [$default_sg]: ${NC}"
        local selected_sg
        read selected_sg
        selected_sg=${selected_sg:-$default_sg}

        if [ -z "$selected_sg" ]; then
            log_error "Security group ID is required to continue"
            exit 1
        fi

        ensure_security_group_rule "$selected_sg" 8000 "0.0.0.0/0"
        ensure_security_group_rule "$selected_sg" 8001 "$staging_cidr"

        associate_instance_profile "$instance_id" "$instance_profile" "$account_id" "$region" "$s3_bucket"
        ensure_instance_tags "$instance_id"
    done

    if confirm "Generate helper script to install/refresh CodeDeploy agent on the instance(s)?"; then
        generate_codedeploy_agent_script "$region"
    fi

    echo ""
    log_info "Existing environment checklist:"
    log_info "  - Copy /tmp/trendsearth-codedeploy-bootstrap.sh to each instance (if generated)"
    log_info "  - Execute with: sudo ./trendsearth-codedeploy-bootstrap.sh"
    log_info "  - Verify CodeDeploy agent is active: sudo systemctl status codedeploy-agent"
    log_info "  - Ensure Docker Swarm services are healthy: docker service ls"
}

ensure_security_group_rule() {
    local sg_id="$1"
    local port="$2"
    local cidr="$3"

    cidr=${cidr:-0.0.0.0/0}

    local tmp_file
    tmp_file=$(mktemp)

    if aws ec2 authorize-security-group-ingress \
        --group-id "$sg_id" \
        --protocol tcp \
        --port "$port" \
        --cidr "$cidr" \
        &> "$tmp_file"; then
        log_success "Security group $sg_id: opened port $port for $cidr"
    else
        if grep -q "InvalidPermission.Duplicate" "$tmp_file"; then
            log_info "Security group $sg_id already allows port $port for $cidr"
        else
            log_warning "Failed to update security group $sg_id for port $port"
            cat "$tmp_file"
        fi
    fi

    rm -f "$tmp_file"
}

associate_instance_profile() {
    local instance_id="$1"
    local desired_profile="$2"
    local account_id="$3"
    local region="$4"
    local s3_bucket="$5"

    local desired_arn="arn:aws:iam::$account_id:instance-profile/$desired_profile"
    local current_profile_arn
    current_profile_arn=$(aws ec2 describe-iam-instance-profile-associations \
        --filters Name=instance-id,Values="$instance_id" \
        --query 'IamInstanceProfileAssociations[0].IamInstanceProfile.Arn' \
        --output text 2>/dev/null)

    local effective_profile

    if [ -z "$current_profile_arn" ] || [ "$current_profile_arn" = "None" ]; then
        effective_profile="$desired_profile"
        if aws ec2 associate-iam-instance-profile \
            --instance-id "$instance_id" \
            --iam-instance-profile Name="$desired_profile" >/dev/null; then
            log_success "Associated instance profile $desired_profile with $instance_id"
            sleep 2
        else
            log_warning "Failed to associate instance profile $desired_profile with $instance_id"
            return
        fi
    else
        effective_profile="${current_profile_arn##*/}"
        if [ "$current_profile_arn" = "$desired_arn" ]; then
            log_success "Instance $instance_id already uses instance profile $desired_profile"
        else
            log_info "Instance $instance_id already uses instance profile $effective_profile"
            log_info "Keeping existing profile and ensuring required permissions."
        fi
    fi

    ensure_profile_role_permissions "$effective_profile" "$account_id" "$region" "$s3_bucket"
}

ensure_profile_role_permissions() {
    local profile_name="$1"
    local account_id="$2"
    local region="$3"
    local s3_bucket="$4"

    if [ -z "$profile_name" ] || [ "$profile_name" = "None" ]; then
        log_warning "No instance profile available to update permissions"
        return
    fi

    if [ -z "$s3_bucket" ]; then
        log_warning "S3 bucket not provided; skipping permission update for profile $profile_name"
        return
    fi

    local attempts=0
    local max_attempts=5
    local role_names=""

    while [ $attempts -lt $max_attempts ]; do
        role_names=$(aws iam get-instance-profile \
            --instance-profile-name "$profile_name" \
            --query 'InstanceProfile.Roles[*].RoleName' \
            --output text 2>/dev/null)
        if [ -n "$role_names" ] && [ "$role_names" != "None" ]; then
            break
        fi
        attempts=$((attempts + 1))
        sleep 2
    done

    if [ -z "$role_names" ] || [ "$role_names" = "None" ]; then
        log_warning "Could not determine roles for instance profile $profile_name"
        return
    fi

    for role_name in $role_names; do
        ensure_role_permissions "$role_name" "$account_id" "$region" "$s3_bucket"
    done
}

ensure_role_permissions() {
    local role_name="$1"
    local account_id="$2"
    local region="$3"
    local s3_bucket="$4"

    local policy_file
    policy_file=$(mktemp)

    cat > "$policy_file" <<EOF
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
                "arn:aws:s3:::$s3_bucket",
                "arn:aws:s3:::$s3_bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams"
            ],
            "Resource": "arn:aws:logs:$region:$account_id:*"
        }
    ]
}
EOF

    if aws iam put-role-policy \
        --role-name "$role_name" \
        --policy-name "TrendsEarthAPIUIDeploymentPolicy" \
        --policy-document "file://$policy_file" >/dev/null; then
        log_success "Updated inline deployment policy on role $role_name"
    else
        log_warning "Failed to update inline deployment policy on role $role_name"
    fi

    rm -f "$policy_file"

    local managed_policies=(
        "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
        "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforAWSCodeDeploy"
    )

    local policy_arn
    for policy_arn in "${managed_policies[@]}"; do
        local already_attached
        already_attached=$(aws iam list-attached-role-policies \
            --role-name "$role_name" \
            --query "AttachedPolicies[?PolicyArn=='$policy_arn'].PolicyArn" \
            --output text 2>/dev/null)

        if [ "$already_attached" = "$policy_arn" ]; then
            log_info "Role $role_name already has managed policy $(basename "$policy_arn")"
        else
            if aws iam attach-role-policy --role-name "$role_name" --policy-arn "$policy_arn" >/dev/null; then
                log_success "Attached managed policy $(basename "$policy_arn") to role $role_name"
            else
                log_warning "Failed to attach managed policy $(basename "$policy_arn") to role $role_name"
            fi
        fi
    done
}

ensure_instance_tags() {
    local instance_id="$1"

    if aws ec2 create-tags --resources "$instance_id" --tags \
        Key=Application,Value="$DEFAULT_APP_TAG_VALUE" \
        Key=$PRODUCTION_TAG_KEY,Value=true \
        Key=$STAGING_TAG_KEY,Value=true \
        >/dev/null; then
        log_success "Applied CodeDeploy tags to $instance_id"
    else
        log_warning "Failed to apply CodeDeploy tags to $instance_id"
    fi
}

generate_codedeploy_agent_script() {
    local region="$1"
    local script_path="/tmp/trendsearth-codedeploy-bootstrap.sh"

    cat > "$script_path" <<'EOF'
#!/bin/bash
set -euo pipefail

LOG_FILE=/var/log/trendsearth-codedeploy-bootstrap.log

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

REGION="%%REGION%%"

log "Starting CodeDeploy agent setup for Trends.Earth API UI"

log "Updating package index"
apt-get update

log "Installing dependencies"
apt-get install -y ruby wget unzip

log "Downloading latest CodeDeploy installer"
cd /tmp
wget -O codedeploy-install https://aws-codedeploy-%%REGION%%.s3.%%REGION%%.amazonaws.com/latest/install
chmod +x codedeploy-install

log "Installing / updating CodeDeploy agent"
./codedeploy-install auto

log "Enabling CodeDeploy agent service"
systemctl enable codedeploy-agent
systemctl start codedeploy-agent

log "Ensuring application directory exists"
mkdir -p /opt/trendsearth-api-ui
chown ubuntu:ubuntu /opt/trendsearth-api-ui

log "Configuring log rotation"
cat > /etc/logrotate.d/trendsearth-api-ui <<'LOGROTATE'
/var/log/trendsearth-*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 ubuntu ubuntu
}
LOGROTATE

log "CodeDeploy agent setup finished"
systemctl status codedeploy-agent --no-pager || true
EOF

    local effective_region
    effective_region=${region:-us-east-1}
    sed -i "s/%%REGION%%/${effective_region}/g" "$script_path"

    chmod +x "$script_path"

    local script_name
    script_name=$(basename "$script_path")

    log_success "Helper script generated: $script_path"
    log_info "Copy to instance with: scp $script_path ubuntu@<instance>:/tmp/"
    log_info "Then run: ssh ubuntu@<instance> 'sudo /tmp/$script_name'"
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
mkdir -p /opt/trendsearth-api-ui
chown ubuntu:ubuntu /opt/trendsearth-api-ui

# Set up log rotation
log "Setting up log rotation..."
cat > /etc/logrotate.d/trendsearth-api-ui <<LOGROTATE
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
    echo "    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=TrendsEarth-UI-Production},{Key=Application,Value=${DEFAULT_APP_TAG_VALUE}},{Key=${PRODUCTION_TAG_KEY},Value=true}]' \\"
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
    echo "    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=TrendsEarth-UI-Staging},{Key=Application,Value=${DEFAULT_APP_TAG_VALUE}},{Key=${STAGING_TAG_KEY},Value=true}]' \\"
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
    log_info "For Production deployments:"
    echo "aws ec2 create-tags --resources i-INSTANCE-ID --tags \\"
    echo "    Key=Application,Value=${DEFAULT_APP_TAG_VALUE} \\"
    echo "    Key=${PRODUCTION_TAG_KEY},Value=true"
    echo ""
    log_info "For Staging deployments:"
    echo "aws ec2 create-tags --resources i-INSTANCE-ID --tags \\"
    echo "    Key=Application,Value=${DEFAULT_APP_TAG_VALUE} \\"
    echo "    Key=${STAGING_TAG_KEY},Value=true"
    echo ""
    log_info "Single instance scenario: add both ${PRODUCTION_TAG_KEY}=true and ${STAGING_TAG_KEY}=true to the same instance."
    
    echo ""
    log_info "To find tagged instances:"
    echo "aws ec2 describe-instances --filters \"Name=tag:${PRODUCTION_TAG_KEY},Values=true\" --query 'Reservations[*].Instances[*].InstanceId' --output text"
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