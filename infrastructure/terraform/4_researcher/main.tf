terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.28.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data source for current caller identity
data "aws_caller_identity" "current" {}

locals {
  researcher_deployed = var.researcher_image_uri != ""
  scheduler_active    = var.scheduler_enabled && local.researcher_deployed

  # Built by: bash .github/scripts/ci/build_one_lambda.sh services/scheduler scheduler
  # path.module is infrastructure/terraform/4_researcher, so ../../.. is the repo root.
  scheduler_zip = "${path.module}/../../../backend/services/scheduler/lambda_function.zip"

  # When var.lambda_artifacts_bucket is set (environment roots), the zip comes
  # from that bucket, where .github/scripts/ci/upload_artifacts.sh puts it.
  # Otherwise the local zip above is used.
  use_s3        = var.lambda_artifacts_bucket != ""
  scheduler_key = "scheduler/lambda_function.zip"
}

# Reads the uploaded zip so a new upload changes s3_object_version and
# redeploys the function. version_id is empty on an unversioned bucket.
data "aws_s3_object" "scheduler" {
  count  = local.scheduler_active && local.use_s3 ? 1 : 0
  bucket = var.lambda_artifacts_bucket
  key    = local.scheduler_key
}

# ECR repository for the researcher Docker image
resource "aws_ecr_repository" "researcher" {
  name                 = "${var.name_prefix}-researcher"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = {
    Project = "alex"
    Part    = "4"
  }
}

# Allow Lambda to pull images from ECR
resource "aws_ecr_repository_policy" "researcher_lambda_access" {
  repository = aws_ecr_repository.researcher.name

  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Sid    = "LambdaEcrImageRetrievalPolicy"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Condition = {
          ArnLike = {
            "aws:sourceArn" = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:*"
          }
        }
      }
    ]
  })
}

# IAM role for researcher Lambda
resource "aws_iam_role" "researcher_lambda_role" {
  name = "${var.name_prefix}-researcher-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project = "alex"
    Part    = "4"
  }
}

# Lambda basic execution policy
resource "aws_iam_role_policy_attachment" "researcher_lambda_basic" {
  role       = aws_iam_role.researcher_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for researcher Lambda to access Bedrock
resource "aws_iam_role_policy" "researcher_lambda_bedrock_access" {
  name = "${var.name_prefix}-researcher-lambda-bedrock-policy"
  role = aws_iam_role.researcher_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ListFoundationModels"
        ]
        Resource = "*"
      }
    ]
  })
}

# Researcher Lambda function
resource "aws_lambda_function" "researcher" {
  count         = local.researcher_deployed ? 1 : 0
  function_name = "${var.name_prefix}-researcher"
  package_type  = "Image"
  image_uri     = var.researcher_image_uri
  role          = aws_iam_role.researcher_lambda_role.arn
  timeout       = 300
  memory_size   = 2048
  architectures = ["x86_64"]

  ephemeral_storage {
    size = 2048
  }

  environment {
    variables = {
      OPENAI_API_KEY    = var.openai_api_key
      ALEX_API_ENDPOINT = var.alex_api_endpoint
      ALEX_API_KEY      = var.alex_api_key
      BEDROCK_REGION    = var.bedrock_region
      RESEARCHER_MODEL  = var.researcher_model
      MCP_LOGGING       = var.mcp_logging
    }
  }

  tags = {
    Project = "alex"
    Part    = "4"
  }
}

# Public function URL for the researcher service
resource "aws_lambda_function_url" "researcher" {
  count              = local.researcher_deployed ? 1 : 0
  function_name      = aws_lambda_function.researcher[0].function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "allow_public_function_url_invoke" {
  count                    = local.researcher_deployed ? 1 : 0
  statement_id             = "AllowPublicFunctionInvokeViaUrl"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.researcher[0].function_name
  principal                = "*"
  invoked_via_function_url = true
}

# IAM role for EventBridge
resource "aws_iam_role" "eventbridge_role" {
  count = local.scheduler_active ? 1 : 0
  name  = "${var.name_prefix}-eventbridge-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project = "alex"
    Part    = "4"
  }
}

# Lambda function for invoking researcher
resource "aws_lambda_function" "scheduler_lambda" {
  count            = local.scheduler_active ? 1 : 0
  function_name    = "${var.name_prefix}-researcher-scheduler"
  role             = aws_iam_role.lambda_scheduler_role[0].arn
  filename         = local.use_s3 ? null : local.scheduler_zip
  source_code_hash = !local.use_s3 && fileexists(local.scheduler_zip) ? filebase64sha256(local.scheduler_zip) : null
  handler          = "lambda_function.handler"
  runtime          = "python3.12"
  timeout          = 180
  memory_size      = 256

  s3_bucket         = local.use_s3 ? var.lambda_artifacts_bucket : null
  s3_key            = local.use_s3 ? local.scheduler_key : null
  s3_object_version = local.use_s3 ? try(coalesce(data.aws_s3_object.scheduler[0].version_id), null) : null

  environment {
    variables = {
      APP_RUNNER_URL          = trimsuffix(aws_lambda_function_url.researcher[0].function_url, "/")
      RESEARCHER_API_KEY      = var.researcher_api_key
      RESEARCH_MODE           = var.research_mode
      RESEARCH_TICKERS        = var.research_tickers
      RESEARCH_SECTOR         = var.research_sector
      RESEARCH_WINDOW         = var.research_window
      REQUEST_TIMEOUT_SECONDS = tostring(var.research_timeout_seconds)
    }
  }

  tags = {
    Project = "alex"
    Part    = "4"
  }
}

# IAM role for scheduler Lambda
resource "aws_iam_role" "lambda_scheduler_role" {
  count = local.scheduler_active ? 1 : 0
  name  = "${var.name_prefix}-scheduler-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project = "alex"
    Part    = "4"
  }
}

# Lambda basic execution policy
resource "aws_iam_role_policy_attachment" "lambda_scheduler_basic" {
  count      = local.scheduler_active ? 1 : 0
  role       = aws_iam_role.lambda_scheduler_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# EventBridge schedule
resource "aws_scheduler_schedule" "research_schedule" {
  count = local.scheduler_active ? 1 : 0
  name  = "${var.name_prefix}-research-schedule"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(2 hours)"

  target {
    arn      = aws_lambda_function.scheduler_lambda[0].arn
    role_arn = aws_iam_role.eventbridge_role[0].arn
  }
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  count         = local.scheduler_active ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler_lambda[0].function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.research_schedule[0].arn
}

# Policy for EventBridge to invoke Lambda
resource "aws_iam_role_policy" "eventbridge_invoke_lambda" {
  count = local.scheduler_active ? 1 : 0
  name  = "InvokeLambdaPolicy"
  role  = aws_iam_role.eventbridge_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.scheduler_lambda[0].arn
      }
    ]
  })
}
