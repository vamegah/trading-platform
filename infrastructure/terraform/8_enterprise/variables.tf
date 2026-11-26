variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_region" {
  description = "AWS region for Bedrock (may differ from main region)"
  type        = string
  default     = "us-west-2"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID to monitor (e.g., amazon.nova-pro-v1:0)"
  type        = string
  default     = "amazon.nova-pro-v1:0"
}

variable "name_prefix" {
  description = "Prefix for resource names. Use a distinct value per environment when several share one AWS account."
  type        = string
  default     = "alex"
}

variable "enabled" {
  description = "Create the CloudWatch dashboards. Each dashboard beyond the free tier costs about $3 per month."
  type        = bool
  default     = true
}

variable "sagemaker_endpoint_name" {
  description = "Name of the SageMaker embedding endpoint shown on the AI model usage dashboard"
  type        = string
  default     = "alex-embedding-endpoint"
}
