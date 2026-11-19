variable "name_prefix" { type = string }
variable "aws_region" { type = string }
variable "bedrock_region" { type = string }
variable "bedrock_model_id" { type = string }
variable "sagemaker_endpoint" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

# SNS
variable "oncall_email" {
  type    = string
  default = ""
}
variable "sns_kms_key_id" {
  type    = string
  default = null
}

# Lambda names (map: short-name -> actual function name)
variable "lambda_names" { type = map(string) }

# Specific Lambda function names for dashboards/alarms
variable "ingest_function_name" { type = string }
variable "search_function_name" { type = string }
variable "researcher_function_name" { type = string }
variable "scheduler_function_name" { type = string }
variable "planner_function_name" { type = string }
variable "tagger_function_name" { type = string }
variable "reporter_function_name" { type = string }
variable "charter_function_name" { type = string }
variable "retirement_function_name" { type = string }
variable "api_function_name" { type = string }

# Queue names (map: short-name -> queue name)
variable "dlq_queue_names" { type = map(string) }
variable "tracked_queue_names" { type = map(string) }

variable "trading_signals_queue_name" { type = string }
variable "analysis_jobs_queue_name" { type = string }

# Thresholds
variable "lambda_error_threshold" {
  type    = number
  default = 1
}
variable "queue_backlog_threshold" {
  type    = number
  default = 10
}
variable "bedrock_5xx_threshold" {
  type    = number
  default = 1
}
variable "aurora_high_acu_threshold" {
  type    = number
  default = 3
}

# Optional Aurora alarm
variable "aurora_cluster_identifier" {
  type    = string
  default = ""
}