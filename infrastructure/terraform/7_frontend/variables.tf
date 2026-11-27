variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

# Clerk validation happens in Lambda, not at API Gateway level
variable "clerk_jwks_url" {
  description = "Clerk JWKS URL for JWT validation in Lambda"
  type        = string
}

variable "clerk_issuer" {
  description = "Clerk issuer URL (kept for Lambda environment)"
  type        = string
  default     = "" # Not actually used but kept for backwards compatibility
}

variable "name_prefix" {
  description = "Prefix for resource names. Use a distinct value per environment when several share one AWS account."
  type        = string
  default     = "alex"
}

variable "lambda_artifacts_bucket" {
  description = "S3 bucket holding the built Lambda zips. Leave empty to use the local zip under backend/."
  type        = string
  default     = ""
}

# Values from the database and agents stacks. Environment roots pass them in
# and set read_sibling_state = false. A standalone run leaves them null and
# reads them from ../5_database and ../6_agents local state.
variable "api_image_uri" {
  description = "ECR image URI for the API Lambda. When set, the function uses package_type Image and the zip settings are ignored. Environment roots pass the image built by build-lambdas.yml."
  type        = string
  default     = ""
}

variable "read_sibling_state" {
  description = "Read database and agents values from the sibling stacks' local state. Environment roots set this to false and pass the values in."
  type        = bool
  default     = true
}

variable "aurora_cluster_arn" {
  description = "ARN of the Aurora cluster from 5_database"
  type        = string
  default     = null
}

variable "aurora_secret_arn" {
  description = "ARN of the Aurora credentials secret from 5_database"
  type        = string
  default     = null
}

variable "database_name" {
  description = "Database name from 5_database"
  type        = string
  default     = null
}

variable "sqs_queue_arn" {
  description = "ARN of the analysis jobs queue from 6_agents"
  type        = string
  default     = null
}

variable "sqs_queue_url" {
  description = "URL of the analysis jobs queue from 6_agents"
  type        = string
  default     = null
}