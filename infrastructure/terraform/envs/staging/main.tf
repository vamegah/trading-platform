# Staging environment root.
#
# Deploys the numbered stacks (2_sagemaker ... 8_enterprise) as modules into one
# state. Values the stacks used to read from each other's local state are passed
# as module outputs below. Environment-specific values come from
# terraform.auto.tfvars.json, which .github/workflows/terraform-apply.yml writes
# from the TFVARS_STAGING secret. See ../README.md.
#
# Each stack declares its own `provider "aws"` block, so none is declared here.
# That also means the module calls below cannot use count, for_each or
# depends_on.

terraform {
  required_version = ">= 1.5"

  # Partial configuration. terraform-apply.yml supplies bucket, key, region and
  # dynamodb_table with -backend-config.
  backend "s3" {}
}

locals {
  environment = "staging"

  # Distinct per environment so staging and prod can share one AWS account
  # without colliding on IAM roles, Lambda names, buckets and so on.
  name_prefix = "trading-${local.environment}"
}

module "sagemaker" {
  source = "../../2_sagemaker"

  aws_region  = var.aws_region
  name_prefix = local.name_prefix
}

module "ingestion" {
  source = "../../3_ingestion"

  aws_region              = var.aws_region
  name_prefix             = local.name_prefix
  lambda_artifacts_bucket = var.lambda_artifacts_bucket
  sagemaker_endpoint_name = module.sagemaker.sagemaker_endpoint_name
}

# The researcher Lambda and its scheduler are created only when
# researcher_image_uri is set. Until then this stack creates only the ECR
# repository and IAM role, which cost nothing.
module "researcher" {
  source = "../../4_researcher"

  aws_region              = var.aws_region
  name_prefix             = local.name_prefix
  lambda_artifacts_bucket = var.lambda_artifacts_bucket
  alex_api_endpoint       = module.ingestion.api_endpoint
  alex_api_key            = module.ingestion.api_key_value
  openai_api_key          = var.openai_api_key
  researcher_image_uri    = var.researcher_image_uri
  scheduler_enabled       = var.scheduler_enabled
  researcher_api_key      = var.researcher_api_key
  bedrock_region          = var.bedrock_region
}

module "database" {
  source = "../../5_database"

  aws_region   = var.aws_region
  name_prefix  = local.name_prefix
  min_capacity = var.db_min_capacity
  max_capacity = var.db_max_capacity
}

module "agents" {
  source = "../../6_agents"

  aws_region              = var.aws_region
  name_prefix             = local.name_prefix
  lambda_artifacts_bucket = var.lambda_artifacts_bucket
  aurora_cluster_arn      = module.database.aurora_cluster_arn
  aurora_secret_arn       = module.database.aurora_secret_arn
  vector_bucket           = module.ingestion.vector_bucket_name
  sagemaker_endpoint      = module.sagemaker.sagemaker_endpoint_name
  bedrock_model_id        = var.bedrock_model_id
  bedrock_region          = var.bedrock_region
  polygon_api_key         = var.polygon_api_key
  polygon_plan            = var.polygon_plan
  langfuse_public_key     = var.langfuse_public_key
  langfuse_secret_key     = var.langfuse_secret_key
  langfuse_host           = var.langfuse_host
  openai_api_key          = var.openai_api_key
}

module "frontend" {
  source = "../../7_frontend"

  aws_region              = var.aws_region
  name_prefix             = local.name_prefix
  lambda_artifacts_bucket = var.lambda_artifacts_bucket
  aurora_cluster_arn      = module.database.aurora_cluster_arn
  aurora_secret_arn       = module.database.aurora_secret_arn
  database_name           = module.database.database_name
  sqs_queue_arn           = module.agents.sqs_queue_arn
  sqs_queue_url           = module.agents.sqs_queue_url

  # The frontend does not use Clerk. The stack variable has no default.
  clerk_jwks_url = ""
}

# CloudWatch dashboards cost about $3 per month each, so they are off unless
# enable_enterprise_dashboards is true.
module "enterprise" {
  source = "../../8_enterprise"

  aws_region              = var.aws_region
  name_prefix             = local.name_prefix
  enabled                 = var.enable_enterprise_dashboards
  bedrock_region          = var.bedrock_region
  bedrock_model_id        = var.bedrock_model_id
  sagemaker_endpoint_name = module.sagemaker.sagemaker_endpoint_name
}
