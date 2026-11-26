variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "min_capacity" {
  description = "Minimum capacity for Aurora Serverless v2 (in ACUs)"
  type        = number
  default     = 0.5
}

variable "max_capacity" {
  description = "Maximum capacity for Aurora Serverless v2 (in ACUs)"
  type        = number
  default     = 1
}

variable "name_prefix" {
  description = "Prefix for resource names. Use a distinct value per environment when several share one AWS account."
  type        = string
  default     = "alex"
}