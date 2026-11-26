variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "sagemaker_endpoint_name" {
  description = "Name of the SageMaker embedding endpoint from Part 2"
  type        = string
  default     = "alex-embedding-endpoint"
}

variable "index_name" {
  description = "S3 Vectors index name for the financial-research knowledge base"
  type        = string
  default     = "financial-research"
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