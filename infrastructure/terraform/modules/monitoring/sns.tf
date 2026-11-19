resource "aws_sns_topic" "alerts" {
  name              = "${var.name_prefix}-alerts"
  display_name      = "${var.name_prefix} platform alerts"
  kms_master_key_id = var.sns_kms_key_id
  tags              = var.tags
}

resource "aws_sns_topic_subscription" "oncall_email" {
  count     = var.oncall_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.oncall_email
}