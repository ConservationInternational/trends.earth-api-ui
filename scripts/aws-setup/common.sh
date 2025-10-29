#!/bin/bash

# Common functions and utilities for AWS setup scripts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "${CYAN}🔧 $1${NC}"
}

# Input validation functions
validate_required() {
    local value="$1"
    local name="$2"
    
    if [ -z "$value" ]; then
        log_error "$name is required"
        return 1
    fi
    return 0
}

validate_aws_region() {
    local region="$1"
    if [[ ! "$region" =~ ^[a-z]{2}-[a-z]+-[0-9]$ ]]; then
        log_error "Invalid AWS region format: $region"
        return 1
    fi
    return 0
}

validate_bucket_name() {
    local bucket="$1"
    # Basic S3 bucket name validation
    if [[ ! "$bucket" =~ ^[a-z0-9][a-z0-9-]*[a-z0-9]$ ]] || [ ${#bucket} -lt 3 ] || [ ${#bucket} -gt 63 ]; then
        log_error "Invalid S3 bucket name: $bucket"
        log_info "Bucket names must be 3-63 characters, lowercase letters, numbers, and hyphens only"
        return 1
    fi
    return 0
}

validate_repository_name() {
    local repo="$1"
    # ECR repository name validation (uses basic grouping for bash compatibility)
    if [[ ! "$repo" =~ ^[a-z0-9]+([._-][a-z0-9]+)*$ ]] || [ ${#repo} -lt 2 ] || [ ${#repo} -gt 256 ]; then
        log_error "Invalid ECR repository name: $repo"
        log_info "Repository names must be 2-256 characters, lowercase letters, numbers, dots, underscores, and hyphens only"
        return 1
    fi
    return 0
}

# AWS CLI validation
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        log_info "Please install it from: https://aws.amazon.com/cli/"
        return 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS CLI is not configured or credentials are invalid"
        log_info "Please run: aws configure"
        return 1
    fi
    
    log_success "AWS CLI is installed and configured"
    return 0
}

# Get AWS account ID
get_aws_account_id() {
    aws sts get-caller-identity --query 'Account' --output text 2>/dev/null
}

# Get current AWS region
get_aws_region() {
    aws configure get region 2>/dev/null || echo "us-east-1"
}

# Prompt for input with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local variable_name="$3"
    
    if [ -n "$default" ]; then
        echo -n -e "${YELLOW}$prompt [$default]: ${NC}"
    else
        echo -n -e "${YELLOW}$prompt: ${NC}"
    fi
    
    local input
    read input
    
    if [ -z "$input" ] && [ -n "$default" ]; then
        input="$default"
    fi
    
    # Use nameref to set the variable
    eval "$variable_name='$input'"
}

# Check if AWS resource exists
check_ecr_repository() {
    local repo_name="$1"
    aws ecr describe-repositories --repository-names "$repo_name" &>/dev/null
}

check_s3_bucket() {
    local bucket_name="$1"
    aws s3api head-bucket --bucket "$bucket_name" &>/dev/null
}

check_iam_role() {
    local role_name="$1"
    aws iam get-role --role-name "$role_name" &>/dev/null
}

check_codedeploy_application() {
    local app_name="$1"
    aws deploy get-application --application-name "$app_name" &>/dev/null
}

# Confirmation prompt
confirm() {
    local prompt="$1"
    echo -n -e "${YELLOW}$prompt (y/N): ${NC}"
    local response
    read response
    [[ "$response" =~ ^[Yy]$ ]]
}

# Error handling
handle_error() {
    local exit_code=$?
    local line_number=$1
    log_error "Script failed at line $line_number with exit code $exit_code"
    exit $exit_code
}

# Set up error handling
set -e
trap 'handle_error $LINENO' ERR