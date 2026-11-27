#!/usr/bin/env bash
# Build the API Lambda container image and push it to ECR.
#
# Usage: build_api_image.sh <ecr repository name> <image tag>
#
# Needs AWS credentials and AWS_REGION. Creates the repository on first use.
# Prints the pushed image URI as the last line of output and, when running in
# GitHub Actions, writes it to $GITHUB_OUTPUT as image_uri.
set -euo pipefail

REPO="$1"   # e.g. trading-staging-api
TAG="$2"    # e.g. the commit SHA
: "${AWS_REGION:?AWS_REGION must be set}"

# This script lives in .github/scripts/ci/, so the repo root is three levels up.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${REGISTRY}/${REPO}:${TAG}"

if ! aws ecr describe-repositories --repository-names "$REPO" >/dev/null 2>&1; then
  echo "Creating ECR repository $REPO"
  aws ecr create-repository \
    --repository-name "$REPO" \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 >/dev/null
  # Keep the 20 most recent images; older ones are no longer deployed.
  aws ecr put-lifecycle-policy \
    --repository-name "$REPO" \
    --lifecycle-policy-text '{"rules":[{"rulePriority":1,"description":"Keep the 20 most recent images","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":20},"action":{"type":"expire"}}]}' >/dev/null
fi

aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY"

# Lambda rejects image indexes, so build a single-platform image without
# provenance or SBOM attestations.
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  -f "$ROOT/infrastructure/docker/api-lambda.Dockerfile" \
  -t "$IMAGE_URI" \
  --push \
  "$ROOT"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "image_uri=${IMAGE_URI}" >> "$GITHUB_OUTPUT"
fi
echo "$IMAGE_URI"
