# Passed by terraform-apply.yml with -var, not through terraform.auto.tfvars.json.
variable "lambda_artifacts_bucket" {
  description = "Existing S3 bucket holding the Lambda zips uploaded by build-lambdas.yml. Terraform reads from it and does not create it."
  type        = string
}

variable "aws_region" {
  description = "AWS region for the stacks"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_region" {
  description = "AWS region used for Bedrock model inference"
  type        = string
  default     = "us-west-2"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID used by the agents"
  type        = string
}

variable "polygon_api_key" {
  description = "Polygon.io API key for market data"
  type        = string
  sensitive   = true
}

variable "polygon_plan" {
  description = "Polygon.io plan type (free or paid)"
  type        = string
  default     = "free"
}

variable "openai_api_key" {
  description = "OpenAI API key for the researcher and for agent tracing. Leave empty to disable."
  type        = string
  default     = ""
  sensitive   = true
}

variable "langfuse_public_key" {
  description = "LangFuse public key for observability (optional)"
  type        = string
  default     = ""
}

variable "langfuse_secret_key" {
  description = "LangFuse secret key for observability (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "langfuse_host" {
  description = "LangFuse host URL (optional)"
  type        = string
  default     = "https://us.cloud.langfuse.com"
}

variable "db_min_capacity" {
  description = "Minimum Aurora Serverless v2 capacity in ACUs"
  type        = number
  default     = 0.5
}

variable "db_max_capacity" {
  description = "Maximum Aurora Serverless v2 capacity in ACUs"
  type        = number
  default     = 1
}

variable "researcher_image_uri" {
  description = "Full ECR image URI for the researcher Lambda. Empty skips the researcher Lambda and its scheduler."
  type        = string
  default     = ""
}

variable "scheduler_enabled" {
  description = "Run the researcher on a schedule. Needs researcher_image_uri and the built scheduler zip."
  type        = bool
  default     = false
}

variable "researcher_api_key" {
  description = "Shared secret sent as x-api-key to the researcher service. Leave empty to disable auth."
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_enterprise_dashboards" {
  description = "Create the CloudWatch dashboards from 8_enterprise (about $3 per month each)"
  type        = bool
  default     = false
}
