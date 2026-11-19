# -------------------------------------------------------- generic Lambda SLOs

locals {
  # Every platform Lambda we want to alarm on
  platform_functions = {
    ingest     = var.ingest_function_name
    search     = var.search_function_name
    researcher = var.researcher_function_name
    scheduler  = var.scheduler_function_name
    planner    = var.planner_function_name
    tagger     = var.tagger_function_name
    reporter   = var.reporter_function_name
    charter    = var.charter_function_name
    retirement = var.retirement_function_name
    api        = var.api_function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = local.platform_functions

  alarm_name          = "${var.name_prefix}-${each.key}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.lambda_error_threshold
  treat_missing_data  = "notBreaching"

  dimensions = { FunctionName = each.value }

  alarm_description = "Lambda ${each.value} has >= ${var.lambda_error_threshold} errors in 5 minutes"
  alarm_actions     = [aws_sns_topic.alerts.arn]
  ok_actions        = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each = local.platform_functions

  alarm_name          = "${var.name_prefix}-${each.key}-throttles"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = { FunctionName = each.value }

  alarm_description = "Lambda ${each.value} is being throttled"
  alarm_actions     = [aws_sns_topic.alerts.arn]
  tags              = var.tags
}

# ------------------------------------------------------------ queue SLOs

resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  for_each = var.dlq_queue_names

  alarm_name          = "${var.name_prefix}-dlq-${each.key}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = { QueueName = each.value }

  alarm_description = "DLQ ${each.value} has messages"
  alarm_actions     = [aws_sns_topic.alerts.arn]
  tags              = var.tags
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog" {
  for_each = var.tracked_queue_names

  alarm_name          = "${var.name_prefix}-backlog-${each.key}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = var.queue_backlog_threshold
  treat_missing_data  = "notBreaching"

  dimensions = { QueueName = each.value }

  alarm_description = "Queue ${each.value} backlog is high"
  alarm_actions     = [aws_sns_topic.alerts.arn]
  tags              = var.tags
}

# ---------------------------------------------------------- researcher SLOs

resource "aws_cloudwatch_metric_alarm" "researcher_failure_rate" {
  alarm_name          = "${var.name_prefix}-researcher-failure-rate"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ResearchFailure"
  namespace           = "Alex/Scheduler"
  period              = 7200
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  alarm_description = "Researcher has failed at least once in the last 2 hours"
  alarm_actions     = [aws_sns_topic.alerts.arn]
  tags              = var.tags
}

# ------------------------------------------------------------ Bedrock SLOs

resource "aws_cloudwatch_metric_alarm" "bedrock_5xx" {
  alarm_name          = "${var.name_prefix}-bedrock-5xx"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "InvocationServerErrors"
  namespace           = "AWS/Bedrock"
  period              = 300
  statistic           = "Sum"
  threshold           = var.bedrock_5xx_threshold

  dimensions = { ModelId = var.bedrock_model_id }

  alarm_description = "Bedrock ${var.bedrock_model_id} is returning 5xx errors"
  alarm_actions     = [aws_sns_topic.alerts.arn]
  tags              = var.tags
}

# ------------------------------------------------------------ Aurora SLOs

resource "aws_cloudwatch_metric_alarm" "aurora_acu_high" {
  count               = var.aurora_cluster_identifier != "" ? 1 : 0
  alarm_name          = "${var.name_prefix}-aurora-high-acu"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 3
  metric_name         = "ServerlessDatabaseCapacity"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.aurora_high_acu_threshold

  dimensions = { DBClusterIdentifier = var.aurora_cluster_identifier }

  alarm_description = "Aurora cluster is above ${var.aurora_high_acu_threshold} ACU"
  alarm_actions     = [aws_sns_topic.alerts.arn]
  tags              = var.tags
}