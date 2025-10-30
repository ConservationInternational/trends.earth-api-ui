#!/bin/bash

# Main AWS Infrastructure Setup Script for Trends.Earth UI
# Orchestrates the setup of all AWS resources needed for ECR + CodeDeploy deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/aws-setup/common.sh"

# Default values
DEFAULT_SETUP_MODE="guided"

main() {
    echo -e "${BLUE}🚀 AWS Infrastructure Setup for Trends.Earth UI${NC}"
    echo "================================================"
    echo ""
    echo "This script will help you set up all the AWS infrastructure needed for"
    echo "ECR + CodeDeploy deployment of the Trends.Earth UI application."
    echo ""
    
    # Check prerequisites
    check_aws_cli || exit 1
    
    local setup_mode
    local components
    
    # Get setup mode
    echo -e "${YELLOW}Choose setup mode:${NC}"
    echo "1. Guided setup (recommended) - Set up all components interactively"
    echo "2. Component selection - Choose specific components to set up"
    echo "3. Quick setup - Use defaults for everything"
    echo ""
    echo -n -e "${YELLOW}Enter choice (1-3) [1]: ${NC}"
    read choice
    
    case "${choice:-1}" in
        1)
            setup_mode="guided"
            ;;
        2)
            setup_mode="selective"
            ;;
        3)
            setup_mode="quick"
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
    
    echo ""
    log_info "Selected mode: $setup_mode"
    echo ""
    
    # Get AWS account info
    local account_id region
    account_id=$(get_aws_account_id)
    region=$(get_aws_region)
    
    log_info "AWS Account Details:"
    log_info "  Account ID: $account_id"
    log_info "  Region: $region"
    echo ""
    
    # Determine which components to set up
    if [ "$setup_mode" = "selective" ]; then
        select_components
    else
        components="ecr s3 iam codedeploy ec2-guide"
    fi
    
    # Setup components
    setup_infrastructure "$components" "$setup_mode"
    
    # Show summary
    show_setup_summary "$account_id" "$region"
}

select_components() {
    echo -e "${YELLOW}Select components to set up:${NC}"
    echo ""
    
    local selected_components=""
    
    if confirm "Set up ECR repository for Docker images?"; then
        selected_components="$selected_components ecr"
    fi
    
    if confirm "Set up S3 bucket for CodeDeploy artifacts?"; then
        selected_components="$selected_components s3"
    fi
    
    if confirm "Set up IAM roles and policies?"; then
        selected_components="$selected_components iam"
    fi
    
    if confirm "Set up CodeDeploy application and deployment groups?"; then
        selected_components="$selected_components codedeploy"
    fi
    
    if confirm "Show EC2 instance setup guide?"; then
        selected_components="$selected_components ec2-guide"
    fi
    
    components="${selected_components# }"  # Remove leading space
    
    if [ -z "$components" ]; then
        log_warning "No components selected. Exiting."
        exit 0
    fi
    
    echo ""
    log_info "Selected components: $components"
    echo ""
}

setup_infrastructure() {
    local components="$1"
    local mode="$2"
    
    echo -e "${CYAN}🔧 Starting infrastructure setup...${NC}"
    echo ""
    
    # Track setup state
    local ecr_repo_name=""
    local s3_bucket_name=""
    local iam_roles_created=false
    
    # ECR Repository
    if [[ "$components" == *"ecr"* ]]; then
        log_step "Setting up ECR repository..."
        if "$SCRIPT_DIR/aws-setup/setup-ecr.sh"; then
            log_success "ECR setup completed"
            ecr_repo_name="trendsearth-api-ui"  # Default name
        else
            log_error "ECR setup failed"
            exit 1
        fi
        echo ""
    fi
    
    # S3 Bucket
    if [[ "$components" == *"s3"* ]]; then
        log_step "Setting up S3 bucket..."
        if "$SCRIPT_DIR/aws-setup/setup-s3.sh"; then
            log_success "S3 setup completed"
            s3_bucket_name="trendsearth-api-ui-codedeploy-artifacts"
        else
            log_error "S3 setup failed"
            exit 1
        fi
        echo ""
    fi
    
    # IAM Roles
    if [[ "$components" == *"iam"* ]]; then
        log_step "Setting up IAM roles..."
        if "$SCRIPT_DIR/aws-setup/setup-iam.sh"; then
            log_success "IAM setup completed"
            iam_roles_created=true
        else
            log_error "IAM setup failed"
            exit 1
        fi
        echo ""
    fi
    
    # CodeDeploy Application
    if [[ "$components" == *"codedeploy"* ]]; then
        log_step "Setting up CodeDeploy application..."
        if [ "$iam_roles_created" = false ]; then
            log_warning "IAM roles were not set up in this session"
            log_info "Assuming they exist from a previous setup..."
        fi
        
        if "$SCRIPT_DIR/aws-setup/setup-codedeploy.sh"; then
            log_success "CodeDeploy setup completed"
        else
            log_error "CodeDeploy setup failed"
            exit 1
        fi
        echo ""
    fi
    
    # EC2 Setup Guide
    if [[ "$components" == *"ec2-guide"* ]]; then
        log_step "Running EC2 setup guide..."
        if "$SCRIPT_DIR/aws-setup/setup-ec2.sh"; then
            log_success "EC2 guide completed"
        else
            log_warning "EC2 guide had issues"
        fi
        echo ""
    fi
}

show_setup_summary() {
    local account_id="$1"
    local region="$2"
    
    echo ""
    echo -e "${GREEN}🎉 Infrastructure Setup Complete!${NC}"
    echo "=================================="
    echo ""
    
    log_info "AWS Resources Created:"
    echo ""
    
    # Check and display created resources
    if check_ecr_repository "trendsearth-api-ui"; then
        local ecr_uri
        ecr_uri=$(aws ecr describe-repositories --repository-names trendsearth-api-ui --query 'repositories[0].repositoryUri' --output text 2>/dev/null)
        log_success "ECR repository detected with default name: $ecr_uri"
    else
        log_info "ECR repository configured (custom name provided during setup; see logs above for details)."
    fi
    
    local default_bucket="trendsearth-api-ui-codedeploy-artifacts"
    if check_s3_bucket "$default_bucket"; then
        log_success "S3 bucket detected with default name: $default_bucket"
    else
        log_info "S3 bucket for CodeDeploy artifacts configured (custom name provided during setup)."
    fi
    
    if check_iam_role "TrendsEarthAPIUICodeDeployRole"; then
        log_success "CodeDeploy service role detected with default name: arn:aws:iam::$account_id:role/TrendsEarthAPIUICodeDeployRole"
    else
        log_info "CodeDeploy service role configured (custom role name supplied)."
    fi
    
    if check_iam_role "TrendsEarthAPIUIInstanceRole"; then
        log_success "EC2 instance role detected with default name: arn:aws:iam::$account_id:role/TrendsEarthAPIUIInstanceRole"
        if aws iam get-instance-profile --instance-profile-name "TrendsEarthAPIUIInstanceProfile" &>/dev/null; then
            log_success "Instance profile detected with default name: arn:aws:iam::$account_id:instance-profile/TrendsEarthAPIUIInstanceProfile"
        fi
    else
        log_info "EC2 instance role and profile configured (custom names supplied during setup)."
    fi
    
    if check_codedeploy_application "trendsearth-api-ui"; then
        log_success "CodeDeploy application detected with default name: trendsearth-api-ui"
        log_info "  Deployment groups with default names: production, staging"
    else
        log_info "CodeDeploy application configured (custom name supplied)."
    fi
    
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo "=============="
    echo ""
    log_info "1. GitHub Secrets Configuration:"
    log_info "   Run: $SCRIPT_DIR/setup-github-secrets.sh"
    echo ""
    log_info "2. EC2 Instance Setup:"
    log_info "   - Launch EC2 instances with the TrendsEarthAPIUIInstanceProfile"
    log_info "   - Use the user data script from the EC2 setup guide"
    log_info "   - Tag instances with Environment=Production or Environment=Staging"
    echo ""
    log_info "3. Verify Installation:"
    log_info "   - Check CodeDeploy agent is running on instances"
    log_info "   - Test ECR authentication"
    log_info "   - Verify Docker Swarm is initialized"
    echo ""
    log_info "4. Test Deployment:"
    log_info "   - Trigger GitHub Actions workflow"
    log_info "   - Monitor deployment in AWS CodeDeploy console"
    log_info "   - Verify application health endpoints"
    echo ""
    
    echo -e "${YELLOW}📚 Documentation:${NC}"
    log_info "  - Setup guide: docs/deployment/aws-infrastructure-setup.md"
    log_info "  - Deployment guide: docs/deployment/README.md"
    echo ""
    
    echo -e "${GREEN}🔗 Useful Commands:${NC}"
    echo ""
    log_info "List CodeDeploy deployments:"
    echo "  aws deploy list-deployments --application-name trendsearth-api-ui"
    echo ""
    log_info "Check instance health:"
    echo "  aws deploy list-deployment-targets --deployment-id <deployment-id>"
    echo ""
    log_info "View CodeDeploy agent logs:"
    echo "  ssh ubuntu@<instance-ip> 'sudo tail -f /var/log/aws/codedeploy-agent/codedeploy-agent.log'"
}

show_help() {
    echo "AWS Infrastructure Setup Script for Trends.Earth UI"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -q, --quick    Quick setup with defaults"
    echo "  -c, --check    Check existing infrastructure"
    echo ""
    echo "This script sets up:"
    echo "  - ECR repository for Docker images"
    echo "  - S3 bucket for CodeDeploy artifacts"
    echo "  - IAM roles and policies"
    echo "  - CodeDeploy application and deployment groups"
    echo "  - EC2 instance setup guidance"
    echo ""
}

check_existing_infrastructure() {
    echo -e "${BLUE}🔍 Checking Existing Infrastructure${NC}"
    echo "=================================="
    echo ""
    
    local account_id region
    account_id=$(get_aws_account_id)
    region=$(get_aws_region)
    
    log_info "Account: $account_id | Region: $region"
    echo ""
    
    # Check ECR
    if check_ecr_repository "trendsearth-api-ui"; then
        log_success "ECR repository 'trendsearth-api-ui' exists"
    else
        log_warning "ECR repository 'trendsearth-api-ui' not found"
    fi
    
    # Check S3
    local bucket="trendsearth-api-ui-codedeploy-artifacts"
    if check_s3_bucket "$bucket"; then
        log_success "S3 bucket '$bucket' exists"
    else
        log_warning "S3 bucket '$bucket' not found"
    fi
    
    # Check IAM roles
    if check_iam_role "TrendsEarthAPIUICodeDeployRole"; then
        log_success "CodeDeploy role 'TrendsEarthAPIUICodeDeployRole' exists"
    else
        log_warning "CodeDeploy role 'TrendsEarthAPIUICodeDeployRole' not found"
    fi
    
    if check_iam_role "TrendsEarthAPIUIInstanceRole"; then
        log_success "EC2 role 'TrendsEarthAPIUIInstanceRole' exists"
    else
        log_warning "EC2 role 'TrendsEarthAPIUIInstanceRole' not found"
    fi
    
    # Check CodeDeploy
    if check_codedeploy_application "trendsearth-api-ui"; then
        log_success "CodeDeploy application 'trendsearth-api-ui' exists"
        
        # Check deployment groups
        if aws deploy get-deployment-group --application-name trendsearth-api-ui --deployment-group-name production &>/dev/null; then
            log_success "Production deployment group exists"
        else
            log_warning "Production deployment group not found"
        fi
        
        if aws deploy get-deployment-group --application-name trendsearth-api-ui --deployment-group-name staging &>/dev/null; then
            log_success "Staging deployment group exists"
        else
            log_warning "Staging deployment group not found"
        fi
    else
        log_warning "CodeDeploy application 'trendsearth-api-ui' not found"
    fi
    
    echo ""
}

# Handle command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -q|--quick)
        setup_mode="quick"
        components="ecr s3 iam codedeploy"
        check_aws_cli || exit 1
        setup_infrastructure "$components" "$setup_mode"
        account_id=$(get_aws_account_id)
        region=$(get_aws_region)
        show_setup_summary "$account_id" "$region"
        exit 0
        ;;
    -c|--check)
        check_aws_cli || exit 1
        check_existing_infrastructure
        exit 0
        ;;
    "")
        # No arguments, run interactive mode
        main "$@"
        ;;
    *)
        log_error "Unknown option: $1"
        echo ""
        show_help
        exit 1
        ;;
esac