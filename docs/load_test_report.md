# Load Test Plan and Baseline

## Target

- 10,000 concurrent users.
- 5,000 instruments.
- Signal/dashboard responses within 500 ms p95 after cache warmup.

## Baseline Assumptions

- Scanner, instrument metadata, and dashboard summaries are Redis cached.
- Market-data ticks fan out through Redis/event-bus topics.
- Agent services autoscale on CPU and queue depth.

## Current Scaffold Estimate

The `/reliability/load-test/estimate` endpoint computes a deterministic estimate for CI and planning. Production load tests should replace it with k6, Locust, or a cloud load-testing service before launch.

The estimate reports concurrent users, instruments, replicas, cache hit rate, estimated origin requests, saturation, p95 latency, bottlenecks, and autoscaling recommendations. A production-ready load gate requires at least 240 minutes of distributed evidence against staging or production-like infrastructure.

## Known Bottlenecks to Watch

- Redis memory and eviction pressure.
- Signal orchestrator queue depth.
- Redis stream lag and event fanout latency.
- Cache hit rate below 90%.
- Broker API rate limits.
- Database connection pool saturation.
