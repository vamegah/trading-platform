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
      replicas = 2
      database_tier = "small"
    }
    staging = {
      replicas = 3
      database_tier = "medium"
    }
    production = {
      replicas = 6
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
