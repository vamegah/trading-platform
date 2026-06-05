variable "phase4_min_replicas" {
  description = "Minimum replicas for phase 4 services."
  type        = number
  default     = 2
}

variable "phase4_max_replicas" {
  description = "Maximum replicas for phase 4 services."
  type        = number
  default     = 10
}

output "phase4_scaling" {
  value = {
    min_replicas = var.phase4_min_replicas
    max_replicas = var.phase4_max_replicas
  }
}
