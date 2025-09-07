#!/bin/bash

# ECR Repository Setup Script for Trends.Earth UI
# Creates ECR repository with lifecycle policies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Default values
DEFAULT_REPOSITORY_NAME="trendsearth-ui"
DEFAULT_REGION="$(get_aws_region)"

main() {
    echo -e "${BLUE}🐳 ECR Repository Setup for Trends.Earth UI${NC}"
    echo "=============================================="
    echo ""
    
    # Check prerequisites
    check_aws_cli || exit 1
    
    local repository_name
    local region
    
    # Get configuration
    log_step "Getting configuration..."
    prompt_with_default "Enter ECR repository name" "$DEFAULT_REPOSITORY_NAME" repository_name
    prompt_with_default "Enter AWS region" "$DEFAULT_REGION" region
    
    # Validate inputs
    validate_required "$repository_name" "Repository name" || exit 1
    validate_repository_name "$repository_name" || exit 1
    validate_required "$region" "AWS region" || exit 1
    validate_aws_region "$region" || exit 1
    
    echo ""
    log_info "Configuration:"
    log_info "  Repository Name: $repository_name"
    log_info "  Region: $region"
    echo ""
    
    # Check if repository already exists
    if check_ecr_repository "$repository_name"; then
        log_warning "ECR repository '$repository_name' already exists"
        if ! confirm "Do you want to update its lifecycle policy?"; then
            log_info "Skipping ECR setup"
            return 0
        fi
        update_lifecycle_policy=true
    else
        update_lifecycle_policy=false
    fi
    
    # Create repository if it doesn't exist
    if [ "$update_lifecycle_policy" = false ]; then
        log_step "Creating ECR repository..."
        if aws ecr create-repository \
            --repository-name "$repository_name" \
            --region "$region" \
            --output text > /dev/null; then
            log_success "ECR repository '$repository_name' created successfully"
        else
            log_error "Failed to create ECR repository"
            exit 1
        fi
    fi
    
    # Set lifecycle policy
    log_step "Setting lifecycle policy..."
    
    local lifecycle_policy='{
        "rules": [
            {
                "rulePriority": 1,
                "description": "Keep last 10 production images",
                "selection": {
                    "tagStatus": "tagged",
                    "tagPrefixList": ["latest", "prod"],
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {
                    "type": "expire"
                }
            },
            {
                "rulePriority": 2,
                "description": "Keep last 5 staging images",
                "selection": {
                    "tagStatus": "tagged",
                    "tagPrefixList": ["staging"],
                    "countType": "imageCountMoreThan",
                    "countNumber": 5
                },
                "action": {
                    "type": "expire"
                }
            },
            {
                "rulePriority": 3,
                "description": "Delete untagged images older than 1 day",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "sinceImagePushed",
                    "countUnit": "days",
                    "countNumber": 1
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }'
    
    if aws ecr put-lifecycle-policy \
        --repository-name "$repository_name" \
        --region "$region" \
        --lifecycle-policy-text "$lifecycle_policy" \
        --output text > /dev/null; then
        log_success "Lifecycle policy applied successfully"
    else
        log_error "Failed to apply lifecycle policy"
        exit 1
    fi
    
    # Get repository URI
    local repository_uri
    repository_uri=$(aws ecr describe-repositories \
        --repository-names "$repository_name" \
        --region "$region" \
        --query 'repositories[0].repositoryUri' \
        --output text)
    
    echo ""
    log_success "ECR setup completed successfully!"
    echo ""
    log_info "Repository Details:"
    log_info "  Name: $repository_name"
    log_info "  URI: $repository_uri"
    log_info "  Region: $region"
    echo ""
    log_info "Next steps:"
    log_info "1. Configure GitHub secrets with AWS credentials"
    log_info "2. Update deployment workflows to use this ECR repository"
    log_info "3. Test image push/pull operations"
    echo ""
    log_info "To test ECR access:"
    echo "  aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $repository_uri"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi