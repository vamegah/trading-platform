# Environment roots

`staging/` and `prod/` are the Terraform roots that `.github/workflows/terraform-apply.yml` runs. `deploy-staging.yml` and `deploy-production.yml` call that workflow.

Each root calls the numbered stacks as modules, so one apply deploys the whole platform into one state file:

| Module | Stack | Notes |
| --- | --- | --- |
| `sagemaker` | `2_sagemaker` | Serverless embedding endpoint. No idle charge. |
| `ingestion` | `3_ingestion` | Vector bucket, ingest Lambda, ingestion API. |
| `researcher` | `4_researcher` | Creates only the ECR repository and an IAM role until `researcher_image_uri` is set. |
| `database` | `5_database` | Aurora Serverless v2. About $43 per month at the default 0.5 ACU minimum. |
| `agents` | `6_agents` | SQS queue and the five agent Lambdas. |
| `frontend` | `7_frontend` | Frontend bucket, CloudFront, API Lambda, HTTP API. |
| `enterprise` | `8_enterprise` | CloudWatch dashboards. Off unless `enable_enterprise_dashboards` is `true`. |

The numbered stacks still work on their own with local state. A root passes them `name_prefix = "trading-<environment>"`, so staging and prod can share one AWS account. The stacks default to `alex`.

## One-time bootstrap

The state bucket and lock table are created by hand, once, with an AWS administrator profile. Terraform does not manage them. The values below are the ones chosen for this project. Substitute your own account ID and names if they differ.

```bash
ACCOUNT_ID=239189624891
REGION=us-east-1
BUCKET=trading-platform-tfstate-$ACCOUNT_ID
TABLE=trading-platform-tflock

aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"   # outside us-east-1 add: --create-bucket-configuration LocationConstraint=$REGION
aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws dynamodb create-table --table-name "$TABLE" --region "$REGION" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

Then set these GitHub repository variables (Settings, Secrets and variables, Actions, Variables). They are names, not secrets:

| Variable | Value |
| --- | --- |
| `TF_STATE_BUCKET` | `trading-platform-tfstate-239189624891` |
| `TF_LOCK_TABLE` | `trading-platform-tflock` |
| `TF_STATE_REGION` | `us-east-1` |

`terraform-apply.yml` passes them to `terraform init` with `-backend-config`. The state key is `envs/<environment>/terraform.tfstate`.

The OIDC role in the `AWS_DEPLOY_ROLE_ARN` secret needs these permissions on top of what the stacks create:

- `s3:ListBucket`, `s3:GetObject`, `s3:PutObject` on the state bucket (`s3:GetBucketVersioning` is optional).
- `dynamodb:GetItem`, `PutItem`, `DeleteItem` on the lock table.
- `s3:GetObject`, `s3:GetObjectVersion` and `s3:ListBucket` on both Lambda artifact buckets. Terraform reads the uploaded zips, and Lambda reads them when it creates or updates a function.

## Lambda artifacts

The build job zips each Lambda and `upload_artifacts.sh` copies the zips to the artifact bucket (`trading-staging-lambda-artifacts`, `trading-prod-lambda-artifacts`). Terraform treats that bucket as an input (`lambda_artifacts_bucket`) and never creates it. The workflow passes the name with `-var`.

Enable versioning on the artifact buckets. Terraform pins each Lambda to the S3 object version it finds. On an unversioned bucket a re-uploaded zip is not detected, so existing functions keep their old code.

## Filling in the tfvars secrets

`terraform-apply.yml` writes the secret `TFVARS_STAGING` or `TFVARS_PROD` to `terraform.auto.tfvars.json` in the root. Create each secret from the matching `terraform.auto.tfvars.json.example`, with the placeholders replaced. Do not commit the real file.

Required values:

| Key | What it is | Where to get it |
| --- | --- | --- |
| `bedrock_model_id` | Bedrock model or inference profile ID the agents call | Bedrock console, Model access or Inference profiles. The model must be enabled in `bedrock_region`. |
| `polygon_api_key` | Polygon.io market data key | Polygon.io dashboard, API keys. |

`aws_region` (default `us-east-1`) and `bedrock_region` (default `us-west-2`) are in the example so you can confirm them. `lambda_artifacts_bucket` is not in the file because the workflow passes it.

Optional values, with their defaults:

| Key | Default | Purpose |
| --- | --- | --- |
| `polygon_plan` | `free` | `free` or `paid`. |
| `openai_api_key` | empty | Researcher and agent tracing. |
| `langfuse_public_key`, `langfuse_secret_key`, `langfuse_host` | empty, empty, `https://us.cloud.langfuse.com` | LangFuse observability. |
| `db_min_capacity`, `db_max_capacity` | `0.5`, `1` | Aurora ACU range. |
| `researcher_image_uri` | empty | ECR image URI. Empty skips the researcher Lambda and scheduler. |
| `scheduler_enabled` | `false` | Run the researcher every 2 hours. Needs `researcher_image_uri`. |
| `researcher_api_key` | empty | Shared `x-api-key` for the researcher. |
| `enable_enterprise_dashboards` | `false` | Create the CloudWatch dashboards. |

The frontend does not use Clerk, so there are no Clerk values.

## Local checks

```bash
terraform -chdir=infrastructure/terraform/envs/staging init -backend=false
terraform -chdir=infrastructure/terraform/envs/staging validate
terraform fmt -check -recursive infrastructure/terraform
```

## Outputs the workflows read

Each root outputs `api_endpoint`, `frontend_bucket` and `cloudfront_distribution_id`. `terraform-apply.yml` exposes them to `deploy-frontend.yml` and the smoke job.
