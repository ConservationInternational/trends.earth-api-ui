#!/bin/bash

# IAM Roles and Policies Setup Script for Trends.Earth UI Deployment
# Creates CodeDeploy service role and EC2 instance role with required policies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Default values
DEFAULT_CODEDEPLOY_ROLE="TrendsEarthUICodeDeployRole"
DEFAULT_EC2_ROLE="TrendsEarthUIInstanceRole"
DEFAULT_INSTANCE_PROFILE="TrendsEarthUIInstanceProfile"

main() {
    echo -e "${BLUE}🔑 IAM Roles Setup for Trends.Earth UI Deployment${NC}"
    echo "=================================================="
    echo ""
    
    # Check prerequisites
    check_aws_cli || exit 1
    
    local codedeploy_role
    local ec2_role
    local instance_profile
    local s3_bucket
    local account_id
    local region
    
    # Get AWS account info
    account_id=$(get_aws_account_id)
    region=$(get_aws_region)
    
    if [ -z "$account_id" ]; then
        log_error "Failed to get AWS account ID"
        exit 1
    fi
    
    # Get configuration
    log_step "Getting configuration..."
    prompt_with_default "Enter CodeDeploy service role name" "$DEFAULT_CODEDEPLOY_ROLE" codedeploy_role
    prompt_with_default "Enter EC2 instance role name" "$DEFAULT_EC2_ROLE" ec2_role
    prompt_with_default "Enter EC2 instance profile name" "$DEFAULT_INSTANCE_PROFILE" instance_profile
    prompt_with_default "Enter S3 bucket name for deployment artifacts" "" s3_bucket
    
    # Validate inputs
    validate_required "$codedeploy_role" "CodeDeploy role name" || exit 1
    validate_required "$ec2_role" "EC2 role name" || exit 1
    validate_required "$instance_profile" "Instance profile name" || exit 1
    validate_required "$s3_bucket" "S3 bucket name" || exit 1
    
    echo ""
    log_info "Configuration:"
    log_info "  CodeDeploy Role: $codedeploy_role"
    log_info "  EC2 Role: $ec2_role"
    log_info "  Instance Profile: $instance_profile"
    log_info "  S3 Bucket: $s3_bucket"
    log_info "  Account ID: $account_id"
    log_info "  Region: $region"
    echo ""
    
    # Create temporary directory for policy files
    local temp_dir
    temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT
    
    # Setup CodeDeploy service role
    setup_codedeploy_role "$codedeploy_role" "$temp_dir"
    
    # Setup EC2 instance role
    setup_ec2_role "$ec2_role" "$instance_profile" "$s3_bucket" "$temp_dir" "$account_id" "$region"
    
    echo ""
    log_success "IAM roles setup completed successfully!"
    echo ""
    log_info "Role ARNs for CodeDeploy configuration:"
    log_info "  CodeDeploy Service Role: arn:aws:iam::$account_id:role/$codedeploy_role"
    log_info "  EC2 Instance Profile: arn:aws:iam::$account_id:instance-profile/$instance_profile"
    echo ""
    log_info "Next steps:"
    log_info "1. Attach the instance profile to your EC2 instances"
    log_info "2. Use the CodeDeploy service role when creating deployment groups"
    log_info "3. Verify the roles have the correct permissions"
}

setup_codedeploy_role() {
    local role_name="$1"
    local temp_dir="$2"
    
    log_step "Setting up CodeDeploy service role..."
    
    # Check if role already exists
    if check_iam_role "$role_name"; then
        log_warning "CodeDeploy role '$role_name' already exists"
        if ! confirm "Do you want to update its policies?"; then
            log_info "Skipping CodeDeploy role setup"
            return 0
        fi
        update_only=true
    else
        update_only=false
    fi
    
    # Create trust policy
    local trust_policy="$temp_dir/codedeploy-trust-policy.json"
    cat > "$trust_policy" <<EOF
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
    
    # Create role if it doesn't exist
    if [ "$update_only" = false ]; then
        if aws iam create-role \
            --role-name "$role_name" \
            --assume-role-policy-document "file://$trust_policy" \
            --output text > /dev/null; then
            log_success "CodeDeploy role '$role_name' created"
        else
            log_error "Failed to create CodeDeploy role"
            exit 1
        fi
    fi
    
    # Attach AWS managed policy
    if aws iam attach-role-policy \
        --role-name "$role_name" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole" \
        --output text > /dev/null; then
        log_success "AWS CodeDeploy managed policy attached"
    else
        log_warning "Failed to attach CodeDeploy managed policy (may already be attached)"
    fi
}

setup_ec2_role() {
    local role_name="$1"
    local instance_profile="$2"
    local s3_bucket="$3"
    local temp_dir="$4"
    local account_id="$5"
    local region="$6"
    
    log_step "Setting up EC2 instance role..."
    
    # Check if role already exists
    if check_iam_role "$role_name"; then
        log_warning "EC2 role '$role_name' already exists"
        if ! confirm "Do you want to update its policies?"; then
            log_info "Skipping EC2 role setup"
            return 0
        fi
        update_only=true
    else
        update_only=false
    fi
    
    # Create trust policy
    local trust_policy="$temp_dir/ec2-trust-policy.json"
    cat > "$trust_policy" <<EOF
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
    
    # Create deployment policy
    local deployment_policy="$temp_dir/ec2-deployment-policy.json"
    cat > "$deployment_policy" <<EOF
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
    
    # Create role if it doesn't exist
    if [ "$update_only" = false ]; then
        if aws iam create-role \
            --role-name "$role_name" \
            --assume-role-policy-document "file://$trust_policy" \
            --output text > /dev/null; then
            log_success "EC2 role '$role_name' created"
        else
            log_error "Failed to create EC2 role"
            exit 1
        fi
    fi
    
    # Attach custom deployment policy
    if aws iam put-role-policy \
        --role-name "$role_name" \
        --policy-name "TrendsEarthUIDeploymentPolicy" \
        --policy-document "file://$deployment_policy" \
        --output text > /dev/null; then
        log_success "Custom deployment policy attached"
    else
        log_error "Failed to attach deployment policy"
        exit 1
    fi
    
    # Attach AWS managed policies
    local managed_policies=(
        "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
        "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforAWSCodeDeploy"
    )
    
    for policy in "${managed_policies[@]}"; do
        if aws iam attach-role-policy \
            --role-name "$role_name" \
            --policy-arn "$policy" \
            --output text > /dev/null; then
            log_success "Attached managed policy: $(basename "$policy")"
        else
            log_warning "Failed to attach managed policy: $policy (may already be attached)"
        fi
    done
    
    # Create instance profile if it doesn't exist
    if aws iam get-instance-profile --instance-profile-name "$instance_profile" &>/dev/null; then
        log_warning "Instance profile '$instance_profile' already exists"
    else
        if aws iam create-instance-profile \
            --instance-profile-name "$instance_profile" \
            --output text > /dev/null; then
            log_success "Instance profile '$instance_profile' created"
        else
            log_error "Failed to create instance profile"
            exit 1
        fi
    fi
    
    # Add role to instance profile
    if aws iam add-role-to-instance-profile \
        --instance-profile-name "$instance_profile" \
        --role-name "$role_name" \
        --output text > /dev/null 2>&1; then
        log_success "Role added to instance profile"
    else
        log_info "Role may already be in instance profile"
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi