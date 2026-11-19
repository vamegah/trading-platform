resource "aws_cloudwatch_dashboard" "ai_model_usage" {
  dashboard_name = "${var.name_prefix}-ai-model-usage"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Bedrock", "Invocations", "ModelId", var.bedrock_model_id, { stat = "Sum", label = "Invocations" }],
            [".", "InvocationClientErrors", ".", ".", { stat = "Sum", label = "Client Errors" }],
            [".", "InvocationServerErrors", ".", ".", { stat = "Sum", label = "Server Errors" }]
          ]
          view   = "timeSeries"
          region = var.bedrock_region
          title  = "Bedrock Invocations (${var.bedrock_model_id})"
          period = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Bedrock", "InputTokenCount", "ModelId", var.bedrock_model_id, { stat = "Sum", label = "Input Tokens" }],
            [".", "OutputTokenCount", ".", ".", { stat = "Sum", label = "Output Tokens" }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.bedrock_region
          title   = "Bedrock Token Usage"
          period  = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Bedrock", "InvocationLatency", "ModelId", var.bedrock_model_id, { stat = "Average", label = "Avg" }],
            [".", ".", ".", ".", { stat = "p99", label = "p99" }]
          ]
          view   = "timeSeries"
          region = var.bedrock_region
          title  = "Bedrock Latency"
          period = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            [{ expression = "SEARCH(' {AWS/SageMaker,EndpointName,VariantName} MetricName=\"Invocations\" EndpointName=\"${var.sagemaker_endpoint}\" ', 'Sum')", id = "s1", label = "Invocations" }],
            [{ expression = "SEARCH(' {AWS/SageMaker,EndpointName,VariantName} MetricName=\"Invocation4XXErrors\" EndpointName=\"${var.sagemaker_endpoint}\" ', 'Sum')", id = "s2", label = "4XX" }],
            [{ expression = "SEARCH(' {AWS/SageMaker,EndpointName,VariantName} MetricName=\"Invocation5XXErrors\" EndpointName=\"${var.sagemaker_endpoint}\" ', 'Sum')", id = "s3", label = "5XX" }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "SageMaker Embedding Endpoint"
          period = 300
        }
      }
    ]
  })
}

resource "aws_cloudwatch_dashboard" "agent_performance" {
  dashboard_name = "${var.name_prefix}-agent-performance"

  # Build metric lists for every platform Lambda
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            for name, arn in var.lambda_names :
            ["AWS/Lambda", "Duration", "FunctionName", name, { stat = "p95", label = name }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Lambda Duration (p95)"
          period = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            for name, arn in var.lambda_names :
            ["AWS/Lambda", "Errors", "FunctionName", name, { stat = "Sum", label = name }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Lambda Errors"
          period = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            for name, arn in var.lambda_names :
            ["AWS/Lambda", "Invocations", "FunctionName", name, { stat = "Sum", label = name }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Lambda Invocations"
          period = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            for name, arn in var.lambda_names :
            ["AWS/Lambda", "Throttles", "FunctionName", name, { stat = "Sum", label = name }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Lambda Throttles"
          period = 300
        }
      }
    ]
  })
}

resource "aws_cloudwatch_dashboard" "researcher" {
  dashboard_name = "${var.name_prefix}-researcher"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["Alex/Scheduler", "ResearchSuccess", { stat = "Sum", label = "Success" }],
            [".", "ResearchFailure", { stat = "Sum", label = "Failure" }],
            [".", "WatchlistLoaded", { stat = "Sum", label = "Watchlist Loaded" }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Researcher Cadence Metrics"
          period = 7200
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", var.researcher_function_name, { stat = "p95" }],
            [".", "Errors", ".", ".", { stat = "Sum" }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Researcher Lambda"
          period = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.trading_signals_queue_name, { stat = "Maximum", label = "Backlog" }],
            [".", "ApproximateAgeOfOldestMessage", ".", ".", { stat = "Maximum", label = "Oldest Age (s)" }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Trading Signals Queue"
          period = 300
        }
      }
    ]
  })
}

resource "aws_cloudwatch_dashboard" "trading" {
  dashboard_name = "${var.name_prefix}-trading"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["Alex/Trading", "SignalsGenerated", { stat = "Sum", label = "Signals" }],
            [".", "TradesPlaced", { stat = "Sum", label = "Trades" }],
            [".", "TradesRejected", { stat = "Sum", label = "Rejected" }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Signals & Trades"
          period = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.analysis_jobs_queue_name, { stat = "Maximum", label = "Analysis Jobs Backlog" }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Analysis Jobs Queue"
          period = 300
        }
      }
    ]
  })
}