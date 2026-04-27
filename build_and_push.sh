#!/usr/bin/env bash
set -e

# Replace these variables with your actual AWS Account ID and region
AWS_REGION="us-east-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME="stream-worker-pipeline"
IMAGE_TAG="latest"

ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}"

echo "Authenticating with ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL

echo "Checking if repository exists, creating if not..."
aws ecr describe-repositories --repository-names ${REPO_NAME} --region $AWS_REGION || aws ecr create-repository --repository-name ${REPO_NAME} --region $AWS_REGION

echo "Building Docker image..."
docker build --platform linux/amd64 -t ${REPO_NAME} .

echo "Tagging image..."
docker tag ${REPO_NAME}:${IMAGE_TAG} ${IMAGE_URI}

echo "Pushing image to ECR: ${IMAGE_URI}"
docker push ${IMAGE_URI}

echo "Done! You can now use '${IMAGE_URI}' as the image_url in your Terraform module."
