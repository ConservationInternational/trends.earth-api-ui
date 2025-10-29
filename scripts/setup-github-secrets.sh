#!/bin/bash

# GitHub Secrets Setup Script for Trends.Earth UI Deployment
# This script helps configure the required GitHub secrets for ECR + CodeDeploy deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_OWNER="ConservationInternational"
REPO_NAME="trends.earth-api-ui"

echo -e "${BLUE}🔐 GitHub Secrets Setup for Trends.Earth UI Deployment${NC}"
echo "========================================================"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) is not installed${NC}"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ Not authenticated with GitHub CLI${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✅ GitHub CLI is installed and authenticated${NC}"
echo ""

# Function to set a secret
set_secret() {
    local secret_name=$1
    local secret_description=$2
    local is_optional=${3:-false}
    
    echo -e "${YELLOW}Setting: ${secret_name}${NC}"
    echo "Description: ${secret_description}"
    
    if [ "$is_optional" = true ]; then
        echo -e "${BLUE}(Optional - press Enter to skip)${NC}"
    fi
    
    echo -n "Enter value: "
    read -s secret_value
    echo ""
    
    if [ -n "$secret_value" ]; then
        if gh secret set "$secret_name" --body "$secret_value" --repo "$REPO_OWNER/$REPO_NAME"; then
            echo -e "${GREEN}✅ Successfully set ${secret_name}${NC}"
        else
            echo -e "${RED}❌ Failed to set ${secret_name}${NC}"
        fi
    elif [ "$is_optional" = false ]; then
        echo -e "${RED}❌ ${secret_name} is required but no value provided${NC}"
        return 1
    else
        echo -e "${YELLOW}⏭️ Skipped ${secret_name}${NC}"
    fi
    echo ""
}

# Function to set a secret from file
set_secret_from_file() {
    local secret_name=$1
    local secret_description=$2
    local file_description=$3
    
    echo -e "${YELLOW}Setting: ${secret_name}${NC}"
    echo "Description: ${secret_description}"
    echo "File: ${file_description}"
    echo -n "Enter file path: "
    read file_path
    
    if [ -f "$file_path" ]; then
        if gh secret set "$secret_name" < "$file_path" --repo "$REPO_OWNER/$REPO_NAME"; then
            echo -e "${GREEN}✅ Successfully set ${secret_name} from file${NC}"
        else
            echo -e "${RED}❌ Failed to set ${secret_name}${NC}"
        fi
    else
        echo -e "${RED}❌ File not found: ${file_path}${NC}"
        return 1
    fi
    echo ""
}

echo "This script will help you configure all the required GitHub secrets."
echo "You can also set these manually in the GitHub repository settings."
echo ""
echo -e "${YELLOW}Press Enter to continue or Ctrl+C to exit...${NC}"
read

echo ""
echo -e "${BLUE}📋 AWS Credentials${NC}"
echo "=================="
set_secret "AWS_ACCESS_KEY_ID" "AWS access key for ECR, CodeDeploy, and S3 access"
set_secret "AWS_SECRET_ACCESS_KEY" "AWS secret key for ECR, CodeDeploy, and S3 access"
set_secret "AWS_REGION" "AWS region (e.g., us-east-1)" true

echo ""
echo -e "${BLUE}🚀 CodeDeploy Configuration${NC}"
echo "==========================="
set_secret "CODEDEPLOY_S3_BUCKET" "S3 bucket for CodeDeploy deployment artifacts"

echo ""
echo -e "${BLUE}📊 Optional Services${NC}"
echo "===================="
set_secret "ROLLBAR_ACCESS_TOKEN" "Rollbar access token for deployment notifications" true

echo ""
echo -e "${GREEN}🎉 GitHub Secrets Setup Complete!${NC}"
echo ""

# Verify secrets were set
echo "Verifying secrets..."
echo ""

# List all secrets to verify
if gh secret list --repo "$REPO_OWNER/$REPO_NAME" &> /dev/null; then
    echo -e "${BLUE}📋 Current repository secrets:${NC}"
    gh secret list --repo "$REPO_OWNER/$REPO_NAME"
else
    echo -e "${RED}❌ Unable to list secrets. Please verify manually in GitHub repository settings.${NC}"
fi

echo ""
echo -e "${YELLOW}⚠️ Important Notes:${NC}"
echo "1. Never commit private keys or sensitive information to the repository"
echo "2. Regularly rotate SSH keys and AWS credentials"
echo "3. Review security group rules to allow only necessary access"
echo "4. Monitor deployment logs for any authentication issues"
echo ""
echo -e "${BLUE}📚 Next Steps:${NC}"
echo "1. Set up AWS infrastructure (see docs/deployment/aws-infrastructure-setup.md)"
echo "2. Test deployment workflows with a manual trigger"
echo "3. Verify application health endpoints are accessible"
echo "4. Set up monitoring and alerting"
echo ""
echo -e "${GREEN}For more information, see: docs/deployment/README.md${NC}"