variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key for the researcher agent"
  type        = string
  sensitive   = true
}

variable "alex_api_endpoint" {
  description = "Alex API endpoint from Part 3"
  type        = string
}

variable "alex_api_key" {
  description = "Alex API key from Part 3"
  type        = string
  sensitive   = true
}

variable "scheduler_enabled" {
  description = "Enable automated research scheduler"
  type        = bool
  default     = false
}

variable "researcher_image_uri" {
  description = "Full ECR image URI for the researcher Lambda container"
  type        = string
  default     = ""
}

variable "bedrock_region" {
  description = "AWS region used for Bedrock model inference"
  type        = string
  default     = "us-west-2"
}

variable "researcher_model" {
  description = "Bedrock model identifier used by the researcher"
  type        = string
  default     = "bedrock/global.openai.gpt-oss-120b-1:0"
}

variable "mcp_logging" {
  description = "Set to exact string True to enable researcher MCP logging"
  type        = string
  default     = "False"
}

# ---------------------------------------------------------------------------
# Scheduler Lambda configuration
# ---------------------------------------------------------------------------

variable "researcher_api_key" {
  description = "Shared secret passed as x-api-key to the researcher service. Leave blank to disable auth."
  type        = string
  sensitive   = true
  default     = ""
}

variable "research_mode" {
  description = "Default research mode for scheduled runs: auto | ticker | sector | macro | topic"
  type        = string
  default     = "auto"
}

variable "research_tickers" {
  description = "Comma-separated tickers for scheduled ticker deep-dives, e.g. 'NVDA,MSFT' (used when research_mode=ticker)"
  type        = string
  default     = ""
}

variable "research_sector" {
  description = "Sector name for scheduled sector scans (used when research_mode=sector)"
  type        = string
  default     = ""
}

variable "research_window" {
  description = "News lookback window for scheduled runs: 24h | 7d"
  type        = string
  default     = "24h"
}

variable "research_timeout_seconds" {
  description = "HTTP timeout in seconds the scheduler Lambda waits for the researcher service"
  type        = number
  default     = 300
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