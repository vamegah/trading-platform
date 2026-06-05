variable "aws_account_id" {
  description = "Expected AWS account id for guarded production applies."
  type        = string
  default     = ""
}

variable "database_username" {
  description = "RDS admin username. Use a secret manager value in production."
  type        = string
  default     = "trading_admin"
}

variable "database_password" {
  description = "RDS admin password. Must be injected by CI/CD secrets in production."
  type        = string
  default     = ""
  sensitive   = true
}

provider "aws" {
  region = var.primary_region
}

data "aws_caller_identity" "current" {}

locals {
  aws_enabled = var.cloud_provider == "aws"
  common_tags = {
    Application = "trading-platform"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_kms_key" "platform" {
  count                   = local.aws_enabled ? 1 : 0
  description             = "Trading platform production encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  tags                    = local.common_tags

  lifecycle {
    precondition {
      condition     = var.environment != "production" || var.aws_account_id == "" || data.aws_caller_identity.current.account_id == var.aws_account_id
      error_message = "Refusing production apply in an unexpected AWS account."
    }
  }
}

resource "aws_s3_bucket" "data_lake" {
  count  = local.aws_enabled ? 1 : 0
  bucket = "trading-platform-${var.environment}-data-lake"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "data_lake" {
  count  = local.aws_enabled ? 1 : 0
  bucket = aws_s3_bucket.data_lake[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  count  = local.aws_enabled ? 1 : 0
  bucket = aws_s3_bucket.data_lake[0].id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.platform[0].arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_db_instance" "postgres" {
  count                   = local.aws_enabled ? 1 : 0
  identifier              = "trading-platform-${var.environment}"
  allocated_storage       = var.environment == "production" ? 200 : 50
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = var.environment == "production" ? "db.m7g.large" : "db.t4g.medium"
  username                = var.database_username
  password                = var.database_password
  backup_retention_period = var.backup_retention_days
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.platform[0].arn
  multi_az                = var.environment == "production"
  skip_final_snapshot     = var.environment != "production"
  tags                    = local.common_tags
}

resource "aws_elasticache_replication_group" "redis" {
  count                         = local.aws_enabled ? 1 : 0
  replication_group_id          = "trading-platform-${var.environment}"
  description                   = "Trading platform Redis/event bus"
  engine                        = "redis"
  node_type                     = var.environment == "production" ? "cache.r7g.large" : "cache.t4g.medium"
  num_cache_clusters            = var.environment == "production" ? 3 : 1
  automatic_failover_enabled    = var.environment == "production"
  transit_encryption_enabled    = true
  at_rest_encryption_enabled    = true
  kms_key_id                    = aws_kms_key.platform[0].arn
  tags                          = local.common_tags
}

output "aws_blueprint" {
  value = {
    enabled              = local.aws_enabled
    kms_key              = local.aws_enabled ? aws_kms_key.platform[0].arn : null
    data_lake_bucket     = local.aws_enabled ? aws_s3_bucket.data_lake[0].bucket : null
    postgres_identifier  = local.aws_enabled ? aws_db_instance.postgres[0].identifier : null
    redis_identifier     = local.aws_enabled ? aws_elasticache_replication_group.redis[0].replication_group_id : null
    production_guarded   = true
    backend_state_needed = true
  }
  sensitive = true
}
