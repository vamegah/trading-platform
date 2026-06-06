variable "backup_retention_days" {
  description = "Database and metadata backup retention."
  type        = number
  default     = 35
}

variable "market_hours_min_replicas" {
  description = "Minimum replicas during market hours."
  type        = number
  default     = 6
}

output "reliability_controls" {
  value = {
    backup_retention_days     = var.backup_retention_days
    market_hours_min_replicas = var.market_hours_min_replicas
    restore_test_required     = true
    slo_uptime_target         = 0.999
    signal_latency_ms         = 500
    redis_stream_lag_target   = 1000
    cache_hit_rate_target     = 0.9
    dr_restore_assets = [
      "database",
      "data_lake_metadata",
      "audit_store",
      "secret_store",
      "redis_event_replay",
    ]
    load_test_target = {
      concurrent_users = 10000
      instruments      = 5000
      p95_latency_ms   = 500
    }
  }
}
