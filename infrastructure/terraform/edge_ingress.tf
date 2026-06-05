variable "frontend_origin_domain_name" {
  description = "DNS name for the frontend origin behind CloudFront."
  type        = string
  default     = ""
}

variable "api_origin_domain_name" {
  description = "DNS name for the API gateway origin behind CloudFront."
  type        = string
  default     = ""
}

variable "waf_rate_limit" {
  description = "Five-minute request limit per source IP enforced at the edge."
  type        = number
  default     = 2000
}

locals {
  edge_enabled = local.aws_enabled && var.enable_edge_ingress
  edge_api_path_patterns = [
    "/api/*",
    "/signals/*",
    "/portfolio/*",
    "/execution/*",
    "/backtest/*",
    "/marketplace/*",
    "/personalization/*",
    "/orchestrator/*",
    "/reliability/*",
  ]
}

resource "aws_wafv2_web_acl" "edge" {
  count       = local.edge_enabled ? 1 : 0
  name        = "trading-platform-${var.environment}-edge"
  description = "Managed rules and rate limits for the trading platform edge"
  scope       = "CLOUDFRONT"
  tags        = local.common_tags

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedCommonRules"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "trading-platform-common-rules"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "SourceIpRateLimit"
    priority = 2

    action {
      block {}
    }

    statement {
      rate_based_statement {
        aggregate_key_type = "IP"
        limit              = var.waf_rate_limit
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "trading-platform-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "trading-platform-edge"
    sampled_requests_enabled   = true
  }
}

resource "aws_cloudfront_distribution" "edge" {
  count               = local.edge_enabled ? 1 : 0
  enabled             = true
  comment             = "Trading platform CDN and API edge"
  default_root_object = "index.html"
  web_acl_id          = aws_wafv2_web_acl.edge[0].arn
  tags                = local.common_tags

  origin {
    domain_name = var.frontend_origin_domain_name
    origin_id   = "frontend-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  origin {
    domain_name = var.api_origin_domain_name
    origin_id   = "api-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "frontend-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = true
      cookies {
        forward = "none"
      }
    }
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.edge_api_path_patterns
    content {
      path_pattern           = ordered_cache_behavior.value
      target_origin_id       = "api-origin"
      viewer_protocol_policy = "redirect-to-https"
      allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods         = ["GET", "HEAD", "OPTIONS"]

      forwarded_values {
        query_string = true
        headers      = ["Authorization", "Content-Type", "X-Request-Id"]
        cookies {
          forward = "all"
        }
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

output "edge_ingress" {
  value = {
    enabled                 = local.edge_enabled
    waf_web_acl_arn         = local.edge_enabled ? aws_wafv2_web_acl.edge[0].arn : null
    cloudfront_distribution = local.edge_enabled ? aws_cloudfront_distribution.edge[0].domain_name : null
    ingress_pattern         = "CloudFront -> WAF -> load balancer -> API gateway/frontend"
  }
}
