terraform {
  required_version = ">= 1.8.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "cloud_provider" {
  description = "Cloud provider blueprint to use."
  type        = string
  default     = "aws"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "primary_region" {
  description = "Primary deployment region."
  type        = string
  default     = "us-east-1"
}

variable "dr_region" {
  description = "Secondary disaster-recovery region."
  type        = string
  default     = "us-west-2"
}

variable "redis_cluster_enabled" {
  description = "Enable Redis cluster mode for signal fanout and cache."
  type        = bool
  default     = true
}

variable "image_tag" {
  description = "Immutable container image tag to deploy."
  type        = string
  default     = "local"
}

variable "enable_live_trading" {
  description = "Enable live trading infrastructure flags. Keep false until legal/compliance signoff."
  type        = bool
  default     = false
}

variable "enable_edge_ingress" {
  description = "Create CloudFront and WAF edge resources for the public event-driven platform ingress."
  type        = bool
  default     = false
}

locals {
  environment_config = {
    dev = {
      replicas      = 2
      database_tier = "small"
    }
    staging = {
      replicas      = 3
      database_tier = "medium"
    }
    production = {
      replicas      = 6
      database_tier = "large"
    }
  }
  selected = lookup(local.environment_config, var.environment, local.environment_config.dev)
  required_services = [
    "api-gateway",
    "external-api-orchestrator",
    "signal-orchestrator",
    "signal-worker",
    "execution-service",
    "execution-worker",
    "portfolio-service",
    "portfolio-worker",
    "safety-service",
    "stress-test-service",
    "backtest-engine",
    "backtest-worker",
    "marketplace-service",
    "marketplace-worker",
    "personalization-engine",
    "personalization-worker",
    "frontend",
    "cloud-load-balancer",
    "cloudfront-cdn",
    "waf",
    "redis",
    "postgres",
    "object-storage",
    "kms",
    "audit-store",
    "secret-store",
  ]
  release_gates = [
    "tests",
    "migration-preflight",
    "terraform-plan",
    "security-scan",
    "smoke-test",
    "manual-approval",
    "rollback-plan",
  ]
}

module "monitoring" {
  source        = "../../modules/monitoring"
  name_prefix   = local.name_prefix
  aws_region    = var.aws_region
  bedrock_region = var.bedrock_region
  bedrock_model_id = var.bedrock_model_id
  sagemaker_endpoint = module.sagemaker_embedding.endpoint_name
  tags          = local.tags
  oncall_email  = var.oncall_email

  lambda_names = {
    ingest     = module.ingest_lambda.function_name
    search     = module.search_lambda.function_name
    researcher = module.researcher.function_name
    scheduler  = module.scheduler.function_name
    planner    = module.planner_lambda.function_name
    tagger     = module.tagger_lambda.function_name
    reporter   = module.reporter_lambda.function_name
    charter    = module.charter_lambda.function_name
    retirement = module.retirement_lambda.function_name
    api        = module.api_lambda.function_name
  }

  ingest_function_name     = module.ingest_lambda.function_name
  search_function_name     = module.search_lambda.function_name
  researcher_function_name = module.researcher.function_name
  scheduler_function_name  = module.scheduler.function_name
  planner_function_name    = module.planner_lambda.function_name
  tagger_function_name     = module.tagger_lambda.function_name
  reporter_function_name   = module.reporter_lambda.function_name
  charter_function_name    = module.charter_lambda.function_name
  retirement_function_name = module.retirement_lambda.function_name
  api_function_name        = module.api_lambda.function_name

  dlq_queue_names = {
    signals  = module.trading_signals_queue.dlq_url   # note: use the queue name, not URL
    jobs     = module.analysis_jobs_queue.dlq_url
  }

  tracked_queue_names = {
    signals = module.trading_signals_queue.queue_url
    jobs    = module.analysis_jobs_queue.queue_url
  }

  trading_signals_queue_name = "${local.name_prefix}-trading-signals"
  analysis_jobs_queue_name   = "${local.name_prefix}-analysis-jobs"

  aurora_cluster_identifier = "${local.name_prefix}-aurora-cluster"
}

output "environment" {
  value = var.environment
}

output "deployment_topology" {
  value = {
    environment           = var.environment
    primary_region        = var.primary_region
    disaster_recovery     = var.dr_region
    redis_cluster_enabled = var.redis_cluster_enabled
    replicas              = local.selected.replicas
    database_tier         = local.selected.database_tier
    image_tag             = var.image_tag
    live_trading_enabled  = var.enable_live_trading
    services              = local.required_services
    release_gates         = local.release_gates
  }
}
