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
