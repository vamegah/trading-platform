output "alerts_topic_arn" {
  value       = aws_sns_topic.alerts.arn
  description = "SNS topic ARN for platform alerts"
}

output "dashboard_names" {
  value = {
    ai_model_usage    = aws_cloudwatch_dashboard.ai_model_usage.dashboard_name
    agent_performance = aws_cloudwatch_dashboard.agent_performance.dashboard_name
    researcher        = aws_cloudwatch_dashboard.researcher.dashboard_name
    trading           = aws_cloudwatch_dashboard.trading.dashboard_name
  }
}

output "dashboard_urls" {
  value = {
    ai_model_usage    = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.ai_model_usage.dashboard_name}"
    agent_performance = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.agent_performance.dashboard_name}"
    researcher        = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.researcher.dashboard_name}"
    trading           = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.trading.dashboard_name}"
  }
}