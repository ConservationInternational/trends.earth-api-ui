#!/bin/bash

# CodeDeploy Application Setup Script for Trends.Earth UI
# Creates CodeDeploy application and deployment groups

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Default values
DEFAULT_APPLICATION_NAME="trendsearth-api-ui"
DEFAULT_CODEDEPLOY_ROLE="TrendsEarthAPIUICodeDeployRole"
APPLICATION_TAG_KEY="Application"
APPLICATION_TAG_VALUE="trendsearth-api-ui"
PRODUCTION_TAG_KEY="CodeDeployGroupProduction"
STAGING_TAG_KEY="CodeDeployGroupStaging"
INSTANCE_TAG_VALUE="true"

main() {
    echo -e "${BLUE}🚀 CodeDeploy Application Setup for Trends.Earth UI${NC}"
    echo "=================================================="
    echo ""
    
    # Check prerequisites
    check_aws_cli || exit 1
    
    local application_name
    local codedeploy_role
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
    prompt_with_default "Enter CodeDeploy application name" "$DEFAULT_APPLICATION_NAME" application_name
    prompt_with_default "Enter CodeDeploy service role name" "$DEFAULT_CODEDEPLOY_ROLE" codedeploy_role
    
    # Validate inputs
    validate_required "$application_name" "Application name" || exit 1
    validate_required "$codedeploy_role" "CodeDeploy role name" || exit 1
    
    # Verify CodeDeploy role exists
    if ! check_iam_role "$codedeploy_role"; then
        log_error "CodeDeploy role '$codedeploy_role' does not exist"
        log_info "Please run setup-iam.sh first to create the required roles"
        exit 1
    fi
    
    local role_arn="arn:aws:iam::$account_id:role/$codedeploy_role"
    
    echo ""
    log_info "Configuration:"
    log_info "  Application Name: $application_name"
    log_info "  Service Role: $codedeploy_role"
    log_info "  Role ARN: $role_arn"
    log_info "  Region: $region"
    echo ""
    
    # Create CodeDeploy application
    setup_codedeploy_application "$application_name"
    
    # Create deployment groups
    setup_deployment_groups "$application_name" "$role_arn"
    
    echo ""
    log_success "CodeDeploy setup completed successfully!"
    echo ""
    log_info "Application Details:"
    log_info "  Name: $application_name"
    log_info "  Deployment Groups: production, staging"
    log_info "  Service Role: $role_arn"
    echo ""
    log_info "Next steps:"
    log_info "1. Tag your EC2 instances with CodeDeploy group tags"
    log_info "2. Ensure CodeDeploy agent is installed and running on instances"
    log_info "3. Test deployment using GitHub Actions workflows"
    echo ""
    log_info "Instance tagging examples:"
    log_info "  Production: ${PRODUCTION_TAG_KEY}=${INSTANCE_TAG_VALUE}"
    log_info "  Staging: ${STAGING_TAG_KEY}=${INSTANCE_TAG_VALUE}"
}

setup_codedeploy_application() {
    local app_name="$1"
    
    log_step "Setting up CodeDeploy application..."
    
    # Check if application already exists
    if check_codedeploy_application "$app_name"; then
        log_warning "CodeDeploy application '$app_name' already exists"
        if ! confirm "Do you want to continue with deployment group setup?"; then
            log_info "Skipping CodeDeploy setup"
            exit 0
        fi
        return 0
    fi
    
    # Create application
    if aws deploy create-application \
        --application-name "$app_name" \
        --compute-platform Server \
        --output text > /dev/null; then
        log_success "CodeDeploy application '$app_name' created"
    else
        log_error "Failed to create CodeDeploy application"
        exit 1
    fi
}

setup_deployment_groups() {
    local app_name="$1"
    local role_arn="$2"
    
    log_step "Setting up deployment groups..."
    
    # Production deployment group
    setup_deployment_group "$app_name" "production" "$role_arn" "$PRODUCTION_TAG_KEY"
    
    # Staging deployment group
    setup_deployment_group "$app_name" "staging" "$role_arn" "$STAGING_TAG_KEY"
}

setup_deployment_group() {
    local app_name="$1"
    local group_name="$2"
    local role_arn="$3"
    local tag_key="$4"
    
    log_step "Creating $group_name deployment group..."
    
    # Check if deployment group already exists
    if aws deploy get-deployment-group \
        --application-name "$app_name" \
        --deployment-group-name "$group_name" &>/dev/null; then
        log_warning "Deployment group '$group_name' already exists"
        if ! confirm "Do you want to update it?"; then
            log_info "Skipping $group_name deployment group"
            return 0
        fi
        
        # Delete existing deployment group
        if aws deploy delete-deployment-group \
            --application-name "$app_name" \
            --deployment-group-name "$group_name" \
            --output text > /dev/null; then
            log_info "Existing deployment group deleted"
        else
            log_warning "Failed to delete existing deployment group"
        fi
    fi
    
    # Create deployment group
    local tag_set="ec2TagSetList=[[{Key=${APPLICATION_TAG_KEY},Value=${APPLICATION_TAG_VALUE},Type=KEY_AND_VALUE},{Key=${tag_key},Value=${INSTANCE_TAG_VALUE},Type=KEY_AND_VALUE}]]"

    if aws deploy create-deployment-group \
        --application-name "$app_name" \
        --deployment-group-name "$group_name" \
        --service-role-arn "$role_arn" \
        --ec2-tag-set "$tag_set" \
        --deployment-config-name CodeDeployDefault.AllAtOnce \
        --auto-rollback-configuration enabled=true,events=DEPLOYMENT_FAILURE,DEPLOYMENT_STOP_ON_ALARM \
        --output text > /dev/null; then
        log_success "$group_name deployment group created"
    else
        log_error "Failed to create $group_name deployment group"
        exit 1
    fi
    
    # Verify deployment group
    log_step "Verifying $group_name deployment group..."
    local instance_count
    instance_count=$(aws deploy list-deployment-instances \
        --deployment-id "fake-deployment-id" \
        --query 'length(instancesList)' \
        --output text 2>/dev/null || echo "0")
    
    log_info "$group_name deployment group configured"
    log_info "  Target instances: Tagged with ${APPLICATION_TAG_KEY}=${APPLICATION_TAG_VALUE} AND $tag_key=$INSTANCE_TAG_VALUE"
    log_info "  Deployment config: CodeDeployDefault.AllAtOnce"
    log_info "  Auto rollback: Enabled on failure"
    echo ""
}

# Function to display instance tagging instructions
show_tagging_instructions() {
    echo ""
    log_info "EC2 Instance Tagging Instructions:"
    echo ""
    log_info "To make instances discoverable by CodeDeploy, apply these tags:"
    echo ""
    log_info "Mandatory application tag:"
    echo "  aws ec2 create-tags --resources i-INSTANCE-ID --tags Key=${APPLICATION_TAG_KEY},Value=${APPLICATION_TAG_VALUE}"
    echo ""
    log_info "Production deployment group tag:"
    echo "  aws ec2 create-tags --resources i-INSTANCE-ID --tags Key=${PRODUCTION_TAG_KEY},Value=${INSTANCE_TAG_VALUE}"
    echo ""
    log_info "Staging deployment group tag:"
    echo "  aws ec2 create-tags --resources i-INSTANCE-ID --tags Key=${STAGING_TAG_KEY},Value=${INSTANCE_TAG_VALUE}"
    echo ""
    log_info "Apply both deployment group tags to the same instance if production and staging share the host."
    echo ""
    log_info "Replace the placeholder instance ID with your actual EC2 instance ID."
    echo ""
    log_warning "Important: Instances must have the CodeDeploy agent installed and running!"
    echo ""
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    show_tagging_instructions
fi