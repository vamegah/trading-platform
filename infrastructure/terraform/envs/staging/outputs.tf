# terraform-apply.yml reads api_endpoint, frontend_bucket and
# cloudfront_distribution_id with `terraform output -raw`. Keep the names.

output "api_endpoint" {
  description = "Base URL of the HTTP API (API Gateway). Routes live under /api/."
  value       = module.frontend.api_gateway_url
}

output "frontend_bucket" {
  description = "S3 bucket that receives the built frontend"
  value       = module.frontend.s3_bucket_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID, used for cache invalidation"
  value       = module.frontend.cloudfront_distribution_id
}

output "cloudfront_url" {
  description = "Public URL of the frontend"
  value       = module.frontend.cloudfront_url
}
