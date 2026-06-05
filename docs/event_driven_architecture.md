# Event-Driven Microservices Architecture

The platform now uses Redis Streams as the durable event backbone. The API gateway accepts commands, publishes them to command streams, and returns `202 Accepted` with a correlation id. Dedicated service workers consume command streams with consumer groups, run the service-owned workflow, and publish result events.

## Ingress And Security

External users, partner fintechs, and third-party developers enter through CloudFront, AWS WAF, and the load balancer defined in `infrastructure/k8s/ingress-edge.yaml` and `infrastructure/terraform/edge_ingress.tf`. The FastAPI gateway applies CORS, rate limiting, audit logging, request ids, and identity propagation before publishing service commands.

## Event Backbone

Each topic maps to `stream:<topic>` in Redis Streams. Messages are also published on Redis pub/sub for low-latency fanout, but service work is driven from streams so commands survive consumer restarts.

| Domain | Command Topic | Result Topic | Consumer Group |
| --- | --- | --- | --- |
| External API Orchestrator | `commands.external_api` | `events.external_api` | `external-api-orchestrator` |
| Signal Orchestrator and AI Agents | `commands.signal` | `events.signal` | `signal-orchestrator` |
| Execution Service | `commands.execution` | `events.execution` | `execution-service` |
| Portfolio and Risk | `commands.portfolio` | `events.portfolio` | `portfolio-service` |
| Backtest Engine | `commands.backtest` | `events.backtest` | `backtest-engine` |
| Marketplace Service | `commands.marketplace` | `events.marketplace` | `marketplace-service` |
| Personalization Engine | `commands.personalization` | `events.personalization` | `personalization-engine` |

## Gateway Commands

The synchronous endpoints remain for compatibility, while production integrations should prefer command endpoints:

- `POST /signals/commands/evaluate`
- `POST /orchestrator/commands/quote`
- `POST /orchestrator/commands/news`
- `POST /execution/commands/smart-route`
- `POST /portfolio/commands/risk/live`
- `POST /backtest/commands/walk-forward`
- `POST /marketplace/commands/agents/publish`
- `POST /marketplace/commands/subscriptions`
- `POST /personalization/commands/events`
- `POST /personalization/commands/persona`

Results can be retrieved by correlation id with `GET /reliability/events/correlations/{correlation_id}`.

## Deployment Units

Docker Compose now runs the gateway, independent HTTP services, and independent stream workers. Kubernetes deployments split the HTTP microservices from worker deployments so API capacity and queue processing can scale separately. Worker HPAs use Redis stream lag metrics such as `redis_stream_lag_commands_signal`.
