#!/bin/bash

# S3 Bucket Setup Script for CodeDeploy Artifacts
# Creates S3 bucket with lifecycle policies for deployment artifacts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Default values
DEFAULT_BUCKET_PREFIX="trendsearth-ui-codedeploy-artifacts"
DEFAULT_REGION="$(get_aws_region)"
DEFAULT_LIFECYCLE_DAYS=30

main() {
    echo -e "${BLUE}🪣 S3 Bucket Setup for CodeDeploy Artifacts${NC}"
    echo "============================================="
    echo ""
    
    # Check prerequisites
    check_aws_cli || exit 1
    
    local bucket_name
    local region
    local lifecycle_days
    local account_id
    
    # Get AWS account ID for unique bucket naming
    account_id=$(get_aws_account_id)
    if [ -z "$account_id" ]; then
        log_error "Failed to get AWS account ID"
        exit 1
    fi
    
    # Generate default bucket name with account ID
    local default_bucket="${DEFAULT_BUCKET_PREFIX}-${account_id}"
    
    # Get configuration
    log_step "Getting configuration..."
    prompt_with_default "Enter S3 bucket name" "$default_bucket" bucket_name
    prompt_with_default "Enter AWS region" "$DEFAULT_REGION" region
    prompt_with_default "Enter lifecycle policy days (delete old artifacts)" "$DEFAULT_LIFECYCLE_DAYS" lifecycle_days
    
    # Validate inputs
    validate_required "$bucket_name" "Bucket name" || exit 1
    validate_bucket_name "$bucket_name" || exit 1
    validate_required "$region" "AWS region" || exit 1
    validate_aws_region "$region" || exit 1
    
    if ! [[ "$lifecycle_days" =~ ^[0-9]+$ ]] || [ "$lifecycle_days" -lt 1 ]; then
        log_error "Lifecycle days must be a positive integer"
        exit 1
    fi
    
    echo ""
    log_info "Configuration:"
    log_info "  Bucket Name: $bucket_name"
    log_info "  Region: $region"
    log_info "  Lifecycle Days: $lifecycle_days"
    echo ""
    
    # Check if bucket already exists
    if check_s3_bucket "$bucket_name"; then
        log_warning "S3 bucket '$bucket_name' already exists"
        if ! confirm "Do you want to update its lifecycle policy?"; then
            log_info "Skipping S3 bucket setup"
            return 0
        fi
        update_lifecycle_only=true
    else
        update_lifecycle_only=false
    fi
    
    # Create bucket if it doesn't exist
    if [ "$update_lifecycle_only" = false ]; then
        log_step "Creating S3 bucket..."
        
        if [ "$region" = "us-east-1" ]; then
            # us-east-1 doesn't need LocationConstraint
            if aws s3api create-bucket \
                --bucket "$bucket_name" \
                --region "$region" \
                --output text > /dev/null; then
                log_success "S3 bucket '$bucket_name' created successfully"
            else
                log_error "Failed to create S3 bucket"
                exit 1
            fi
        else
            # Other regions need LocationConstraint
            if aws s3api create-bucket \
                --bucket "$bucket_name" \
                --region "$region" \
                --create-bucket-configuration LocationConstraint="$region" \
                --output text > /dev/null; then
                log_success "S3 bucket '$bucket_name' created successfully"
            else
                log_error "Failed to create S3 bucket"
                exit 1
            fi
        fi
        
        # Enable versioning
        log_step "Enabling versioning..."
        if aws s3api put-bucket-versioning \
            --bucket "$bucket_name" \
            --versioning-configuration Status=Enabled \
            --output text > /dev/null; then
            log_success "Versioning enabled"
        else
            log_warning "Failed to enable versioning"
        fi
        
        # Block public access
        log_step "Blocking public access..."
        if aws s3api put-public-access-block \
            --bucket "$bucket_name" \
            --public-access-block-configuration \
                BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true \
            --output text > /dev/null; then
            log_success "Public access blocked"
        else
            log_warning "Failed to block public access"
        fi
    fi
    
    # Set lifecycle policy
    log_step "Setting lifecycle policy..."
    
    local lifecycle_policy='{
        "Rules": [
            {
                "ID": "DeleteOldDeploymentArtifacts",
                "Status": "Enabled",
                "Filter": {
                    "Prefix": "deployments/"
                },
                "Expiration": {
                    "Days": '$lifecycle_days'
                }
            },
            {
                "ID": "DeleteIncompleteMultipartUploads",
                "Status": "Enabled",
                "Filter": {},
                "AbortIncompleteMultipartUpload": {
                    "DaysAfterInitiation": 7
                }
            },
            {
                "ID": "DeleteOldVersions",
                "Status": "Enabled",
                "Filter": {},
                "NoncurrentVersionExpiration": {
                    "NoncurrentDays": 30
                }
            }
        ]
    }'
    
    if aws s3api put-bucket-lifecycle-configuration \
        --bucket "$bucket_name" \
        --lifecycle-configuration "$lifecycle_policy" \
        --output text > /dev/null; then
        log_success "Lifecycle policy applied successfully"
    else
        log_error "Failed to apply lifecycle policy"
        exit 1
    fi
    
    # Set bucket policy for CodeDeploy access
    log_step "Setting bucket policy for CodeDeploy access..."
    
    local bucket_policy='{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCodeDeployAccess",
                "Effect": "Allow",
                "Principal": {
                    "Service": "codedeploy.amazonaws.com"
                },
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::'$bucket_name'",
                    "arn:aws:s3:::'$bucket_name'/*"
                ]
            }
        ]
    }'
    
    if aws s3api put-bucket-policy \
        --bucket "$bucket_name" \
        --policy "$bucket_policy" \
        --output text > /dev/null; then
        log_success "Bucket policy applied successfully"
    else
        log_warning "Failed to apply bucket policy (this may be expected if CodeDeploy service doesn't exist in region)"
    fi
    
    echo ""
    log_success "S3 bucket setup completed successfully!"
    echo ""
    log_info "Bucket Details:"
    log_info "  Name: $bucket_name"
    log_info "  Region: $region"
    log_info "  Lifecycle: Delete artifacts after $lifecycle_days days"
    echo ""
    log_info "GitHub Secret Configuration:"
    log_info "  CODEDEPLOY_S3_BUCKET: $bucket_name"
    echo ""
    log_info "Next steps:"
    log_info "1. Set GitHub secret CODEDEPLOY_S3_BUCKET to: $bucket_name"
    log_info "2. Ensure CodeDeploy service role has access to this bucket"
    log_info "3. Test deployment artifact uploads"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi