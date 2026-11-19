#!/usr/bin/env bash
set -euo pipefail

BUCKET="$1"
SHA="$2"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

upload() {
  local local_path="$1"
  local s3_key="$2"
  if [[ ! -f "$local_path" ]]; then
    echo "Missing artifact: $local_path" >&2
    exit 1
  fi
  echo "Uploading $local_path -> s3://$BUCKET/$s3_key"
  aws s3 cp "$local_path" "s3://$BUCKET/$s3_key" \
    --metadata "git-sha=$SHA" \
    --no-progress
}

upload "$ROOT/backend/services/portfolio_planner/planner.zip"            "planner/planner_lambda.zip"
upload "$ROOT/backend/services/agents/instrument_tagger/tagger.zip"      "tagger/tagger_lambda.zip"
upload "$ROOT/backend/services/agents/report_writer/reporter.zip"        "reporter/reporter_lambda.zip"
upload "$ROOT/backend/services/agents/chart_maker/charter.zip"           "charter/charter_lambda.zip"
upload "$ROOT/backend/services/agents/retirement_specialist/retirement.zip" "retirement/retirement_lambda.zip"
upload "$ROOT/backend/services/agents/researcher_agent/researcher.zip"   "researcher/researcher.zip"
upload "$ROOT/backend/services/scheduler/scheduler.zip"                  "scheduler/scheduler.zip"
upload "$ROOT/backend/services/knowledge_base/ingest/knowledge_base.zip" "knowledge_base/ingest.zip"
upload "$ROOT/backend/services/knowledge_base/ingest/knowledge_base.zip" "knowledge_base/search.zip"
upload "$ROOT/backend/api_gateway/api.zip"                               "api/api_lambda.zip"

echo "All artifacts uploaded for $SHA"