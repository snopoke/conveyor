# Gumption — Self-hosted Task Queue Observability

> Source of truth: the original design doc (2026-11-25). This Markdown copy is what agents read. Changes to it are human-owned (see `docs/harness/ownership.md`); propose edits through an ADR in `docs/adr/`.

## Summary

Gumption is an open-source, self-hosted observability service for background task systems: Celery first, any queue through an SDK. It ships as one Go binary backed by PostgreSQL (metadata) and ClickHouse (events), with a React UI that consumes only the public API.

Today, Celery teams choose between Flower (live state, little history, no alerting) and a hand-assembled Prometheus exporter + Grafana stack (metrics, but no per-run drill-down or error grouping). Gumption combines both views: Sentry-style grouping by task type, run-level drill-down, queue health, and alerts, in one product a small team can run.

### Goals

- Answer "is my task system healthy, and if not, which task, queue or tenant is the problem?" in under 10 seconds from the landing page.
- Work without Celery: a small, documented event protocol any SDK can speak.
- Run on one VM via Docker Compose and scale out to Kubernetes without code changes.
- Be built and maintained primarily by AI agents, with guardrails that keep the code correct and the architecture intact.

### Non-goals

- Billing, plans, quotas, or multi-organisation tenancy. One install = one organisation.
- General APM, log management, or distributed tracing. Gumption tracks task runs, not spans.
- Controlling workers (restart, scale, revoke, purge). Gumption stays read-only (decided: D-004).

### Requirement coverage

| Requirement | Where it is addressed |
| --- | --- |
| Dashboards (built-in and custom) | Metrics catalogue; Frontend |
| Total tasks over time by terminal status | Metrics catalogue: throughput |
| Queue depth | Ingestion: broker probes; Metrics catalogue |
| Error rate | Metrics catalogue |
| Stale tasks | Metrics catalogue: stale and lost runs |
| Execution time spread, global and per task type | Metrics catalogue: duration distribution |
| Slowest tasks | Metrics catalogue; Frontend: task type page |
| Queue wait time per queue | Metrics catalogue: wait time |
| Tags for filtering and aggregation (e.g. tenant) | Domain model; Storage: promoted tags |
| Slack alerts on wait time and depth thresholds | Alerting |
| Instatus and other monitoring integrations | Alerting: integrations; Prometheus export |
| Sentry-like list grouped by task type | Frontend: task list |
| Tasks belong to a project; invite-based project access; single org | Access model |
| Open source, self-hosted | Deployment; licence in Open questions |
| SDK-based, not tied to Celery | Ingestion |
| Pluggable architecture with clear modules | Architecture; Plugin architecture |
| AI-suitable stack, AI guardrails, AI-owned codebase | Tech stack; AI ownership and guardrails |
| Simple, clean, fun UI | Frontend |
| Fully documented, API native | API design; Deployment and documentation |

## Core concepts and domain model

Everything reduces to one stream: immutable **task events** that are stitched into **task runs**. Every metric, list, and alert is a query over runs, events, or queue samples.

| Concept | Definition | Identity |
| --- | --- | --- |
| Organisation | The install itself. Implicit, never modelled as a row. | n/a |
| Project | A unit of ownership and access, e.g. "ocs-prod". Owns ingest keys, runs, alert rules, dashboards. | `project_id` (UUID) + slug |
| Environment | A free-form label on events (`prod`, `staging`), filterable everywhere. Avoids one project per environment. | string |
| Task type | A task's name, e.g. `apps.chat.tasks.send_message`. The grouping key for the Sentry-style list. | (project, `task_name`) |
| Queue | The routing destination a run was sent to. Tracked for wait time and depth. | (project, `queue`) |
| Task run | One execution attempt of one task. Has a lifecycle state, timings, worker, and tags. Retries create new attempts of the same run. | (project, `task_id`, `attempt`) |
| Task event | An immutable fact about a run: `enqueued`, `started`, `heartbeat`, `succeeded`, `failed`, `retried`, `revoked`, `rejected`. | `event_id` (UUIDv7, client-generated) |
| Worker | A process that executes runs. Sends worker heartbeats so lost runs can be detected. | (project, `worker_id`) |
| Queue sample | A point-in-time depth reading for a queue, from a broker probe or an SDK. | (project, `queue`, ts) |
| Error group | Failed runs grouped by fingerprint: task name + exception type + top in-app frame. Has a status (open, resolved, ignored). | (project, `fingerprint`) |
| Tag | A key/value pair on a run, e.g. `tenant=acme`, `team_id=42`. Set at enqueue time and propagated to the worker. | key, value |

### Run lifecycle

A run moves `enqueued → started → (succeeded | failed | retried | revoked | rejected)`. `succeeded`, `failed`, `revoked` and `rejected` are terminal. `retried` is terminal for that attempt and opens attempt n+1. Two derived states are computed, never sent: **stale** (started, no terminal event or heartbeat within its threshold) and **lost** (its worker stopped sending heartbeats while it was running).

Events may arrive out of order or more than once. The merge rules are commutative: earliest `enqueued_at` and `started_at` win, latest `finished_at` wins, and the state is the one with the highest lifecycle rank, with ties broken by timestamp. Duplicates collapse on `event_id`. These rules are the single most important invariant in the system and carry property-based tests.

### Tags

Tags are a `Map(String, String)` on every run, limited to 32 keys, 64-character keys and 200-character values per run. Any tag is filterable. A project can **promote** up to 5 tag keys (e.g. `tenant`); promoted tags get pre-aggregated rollups, so they can be grouped on dashboards and used in alert rules cheaply. Unpromoted tags are filterable but aggregate from raw runs, which is slower over long ranges.

## Architecture overview

Gumption is a modular monolith: one Go binary, split into modules with enforced import rules, deployed in one or more roles. Writes enter only through Ingest; every read (UI, API, alerts, dashboards) goes through one Query module and one query type, `MetricQuery`.

All writes go through Ingest; all reads go through Query.

```
 Sources                     gumption binary (Go)                 Stores / outputs
┌───────────────────────┐   ┌──────────────────────────────┐    ┌────────────────────────────┐
│ Celery apps           │──▶│ Ingest                       │───▶│ ClickHouse                 │
│ (gumption-celery)     │   │ auth, validate, batch, write │───▶│ events, runs, rollups      │
├───────────────────────┤   ├──────────────────────────────┤    ├────────────────────────────┤
│ Any queue system      │──▶│ Query  ◀── one MetricQuery   │───▶│ ClickHouse / PostgreSQL    │
│ (Python/Node/Go, HTTP)│   │        for all reads         │    │ users, projects, rules     │
├───────────────────────┤   ├──────────────────────────────┤    ├────────────────────────────┤
│ Broker probes         │──▶│ Alerting (a Query client)    │───▶│ Notifier plugins           │
│ (Redis, RabbitMQ, SQS)│   │ rules, state machine         │    │ Slack, Instatus, webhooks  │
└───────────────────────┘   ├──────────────────────────────┤    ├────────────────────────────┤
                            │ Public API ──▶ Query         │◀───│ Web UI, CLI, scripts       │
                            │ REST, OpenAPI 3.1, authz     │    │ (all use the public API)   │
                            └──────────────────────────────┘    └────────────────────────────┘
```

The Web UI has no private endpoints: if the UI can do it, a script can do it with an API token. Alerting is just another Query client, so an alert can be defined on any chart a user can draw.

### Modules and boundaries

Each module is a Go package under `internal/` with a public interface file (`port.go`) and private implementation. Arrows below are the only allowed imports; CI fails on any other (see AI guardrails).

| Module | Owns | May import |
| --- | --- | --- |
| `platform` | Config, logging, self-metrics, clock, ID generation | stdlib only |
| `domain` | Event, run, and query types; merge rules; validation. Pure code, no I/O | `platform` |
| `ingest` | HTTP intake, ingest-key auth, decoding, validation, batching, write to `EventSink` | `domain`, `eventstore` port, `metastore` port |
| `eventstore` | `EventStore` port + ClickHouse adapter: inserts, run stitching, rollups, retention | `domain` |
| `metastore` | PostgreSQL via sqlc: projects, users, rules, dashboards, error-group status | `domain` |
| `query` | Turns `MetricQuery` and `RunListQuery` into store reads; picks raw, 1-minute or 1-hour tier | `domain`, `eventstore` port |
| `identity` | Users, sessions, invites, API tokens, project membership, authorisation checks | `domain`, `metastore` port |
| `alerting` | Rule evaluation, alert state machine, dispatch with cooldown | `domain`, `query`, `metastore` port, `notify` port |
| `notify` | `Notifier` port + built-in plugins (Slack, Instatus, webhook, email) | `domain` |
| `probes` | `BrokerProbe` port + plugins; scheduled depth sampling | `domain`, `ingest` sink |
| `api` | Handlers generated from OpenAPI; thin mapping to services | service ports only, never adapters |
| `web` | React SPA, embedded in the binary with `go:embed` | generated API client only |

### Process roles

The binary runs as `gumption serve --roles=api,ingest,worker` (all three by default). `ingest` scales horizontally behind a load balancer. `worker` runs the alert evaluator, broker probes, and retention jobs; when several worker replicas run, one holds a PostgreSQL advisory lock and the rest stand by. No Redis, no message bus: two stateful dependencies in total.

## Ingestion: protocol, SDKs, Celery integration

All data arrives as batches of task events over one HTTP endpoint, authenticated by a per-project ingest key (DSN-style, like Sentry). The protocol is versioned and published as a JSON Schema, so an SDK in any language is a few hundred lines.

### Wire protocol (v1)

- `POST /ingest/v1/events`, header `Authorization: Bearer <ingest key>`, body is gzip-compressed NDJSON, one event per line, at most 1,000 events or 1 MB per request.
- Response `202` with counts of accepted and rejected events and a reason per rejected line. Ingest never fails a whole batch because of one bad event.
- SDKs buffer in memory, flush every 2 seconds or at 500 events, retry with jittered backoff, and drop (counting drops) when the buffer passes a cap. Monitoring must never slow down or crash the application it monitors.
- `POST /ingest/v1/queue-samples` takes depth readings from SDK-side probes.

```json
{"v":1,"event_id":"0193f0c2-...","type":"failed","ts":"2026-11-25T18:04:11.532Z",
 "task_id":"b7e1...","attempt":2,"task_name":"apps.chat.tasks.send_message","queue":"chat",
 "env":"prod","worker_id":"celery@ip-10-0-3-12:4711","duration_ms":8412,
 "tags":{"tenant":"acme","team_id":"42"},
 "error":{"type":"httpx.ReadTimeout","message":"...","stack":[...],"fingerprint":null}}
```

Event IDs are UUIDv7 generated by the client, so retries are idempotent and IDs sort by time. `fingerprint` is optional; the server computes one when it is absent. Stack traces are truncated to 50 frames and 64 KB.

### Celery integration (`gumption-celery`)

A pip-installable package configured with one call, `gumption_celery.init(app, dsn=...)`. It hooks Celery signals rather than the Celery event stream, because signals need no broker-side event traffic and run in-process with full context.

| Signal | Emits | Notes |
| --- | --- | --- |
| `before_task_publish` | `enqueued` | Adds headers `gumption_enqueued_at` and `gumption_tags`, so wait time and tags survive the hop to the worker |
| `task_prerun` | `started` | Reads the headers back and sets the tag context for the run |
| `task_success` / `task_postrun` | `succeeded` | Duration measured with a monotonic clock in the worker |
| `task_failure` | `failed` | Exception type, message, stack trace |
| `task_retry` | `retried` | Next attempt's ETA, if any |
| `task_revoked`, `task_rejected`, `task_unknown` | `revoked`, `rejected` |  |
| `worker_ready`, timer thread | worker heartbeat | Every 30 s, used for lost-run detection |

Tags are set at publish time through a context manager or a per-task hook:

```python
with gumption.tags(tenant=team.slug):
    send_message.delay(msg.id)

# or derive tags from task arguments, declared once
@gumption.tag_with(lambda args, kwargs: {"tenant": kwargs["team_slug"]})
@app.task
def send_message(msg_id, team_slug): ...
```

For teams that cannot touch application code, an optional `gumption-celery-listener` sidecar consumes the Celery event stream instead. It works with `worker_send_task_events` enabled but has less context (no tags, no publish timestamp unless `task_send_sent_event` is on). It is documented as the fallback, not the default.

### Other SDKs and integrations

V1 ships a core Python SDK (framework-agnostic `gumption.track()` context manager) plus the Celery integration. Node (BullMQ) and Go (asynq, River) follow in later milestones. Each integration must pass a shared conformance suite: it replays a scripted workload against a fake ingest server and compares the captured events with a golden file.

### Broker probes

Queue depth is read from the broker, because events alone cannot see messages that were published by something without an SDK. Probes run in the `worker` role (or as a tiny sidecar where the broker is not reachable from Gumption) and sample every 15 seconds: Redis `LLEN` per queue key, RabbitMQ management API `messages_ready`, SQS `ApproximateNumberOfMessages`. When no probe is configured, depth falls back to an estimate: enqueued minus started over a sliding window, labelled as an estimate in the UI.

### Clock skew

Wait time compares a producer's clock with a worker's clock. The server records its own receive time for every event, and the UI warns when a project's median skew (event `ts` against receive time) exceeds 2 seconds. Run durations use the worker's monotonic clock and are unaffected.

## Storage and query

High-volume, append-only task data lives in ClickHouse; low-volume, relational, transactional data lives in PostgreSQL. Each store is behind a port, so a second event store can be added without touching Query or the API. v1 ships a PostgreSQL/TimescaleDB "lite" `EventStore` for small installs alongside the ClickHouse default (decided: D-003; feature m4-010).

### ClickHouse tables

| Table | Engine | Grain | Default retention | Used for |
| --- | --- | --- | --- | --- |
| `task_events` | MergeTree, partitioned by day, ordered by (project, task_name, ts) | one row per event | 7 days | Run timeline, debugging, re-stitching |
| `task_runs` | AggregatingMergeTree, ordered by (project, task_id, attempt) | one row per run attempt | 30 days | Run lists, slowest runs, stale detection, ad-hoc tag queries |
| `task_stats_1m` | AggregatingMergeTree | project × env × task × queue × status × minute | 30 days | Every dashboard chart up to 30 days |
| `task_stats_1h` | AggregatingMergeTree | same, hourly | 13 months | Long-range charts |
| `task_stats_tag_1m` | AggregatingMergeTree | adds promoted tag key + value | 30 days | Group-by-tenant charts and per-tag alerts |
| `queue_samples` | MergeTree | project × queue × sample | 30 days raw, then hourly max | Queue depth |
| `worker_heartbeats` | ReplacingMergeTree | project × worker, latest only | 1 day | Lost-run detection, worker list |

`task_runs` is filled by a materialized view from `task_events`. Each column uses a merge function that matches the merge rules in the domain model: `min` for `enqueued_at` and `started_at`, `max` for `finished_at`, `argMax` by lifecycle rank for `state`. Partial events (a `started` without an `enqueued`) therefore merge correctly in any order, with no read-modify-write in the ingest path.

Rollup tables store `countState`, `sumState`, and `quantilesTDigestState` for run time and wait time, plus a fixed log-scale histogram `(``40 buckets from 1 ms to 6 hours``, merged with sumForEach``)` for heatmaps. Rollups are populated by materialized views at insert time, so dashboards never scan raw runs unless a filter needs an unpromoted tag.

### PostgreSQL schema (abridged)

`users`, `sessions`, `projects`, `project_members` (role), `invites`, `api_tokens` (hashed), `ingest_keys` (hashed, per project), `alert_rules`, `alert_events` (state history), `integrations` (config encrypted with a key from the environment), `dashboards` (JSON panel definitions), `error_groups` (status, assignee, first/last seen), `promoted_tags`, `audit_log`. All access is through sqlc-generated, typed queries; migrations are SQL files run by the binary at startup.

### Query tier selection

The Query module picks the cheapest source that can answer exactly: 1-hour rollups for ranges over 7 days, 1-minute rollups otherwise, raw `task_runs` only when a filter uses an unpromoted tag or the question is about individual runs. The chosen tier is returned in every response (`"source":"rollup_1m"`) so the UI can show it and tests can assert it.

### Performance targets

| Measure | Target, single 4 vCPU / 16 GB node |
| --- | --- |
| Sustained ingest | 10,000 events/s |
| Ingest-to-visible latency | p95 under 5 s |
| Dashboard query, 24 h range | p95 under 300 ms |
| Dashboard query, 30 d range | p95 under 1 s |
| Alert evaluation lag | under 60 s from event to notification |

These are targets to validate with the load simulator in M1, not measured numbers.

## Metrics catalogue

Every required metric is a named metric in one query model. A `MetricQuery` is `{metric, aggregation, filters, group_by, interval, range}`; the same object drives a dashboard panel, an alert rule, and an API call, so there is one implementation and one set of tests per metric.

```json
{"metric":"run.wait_time","aggregation":"p95",
 "filters":{"env":"prod","queue":["chat","default"],"tag.tenant":"acme"},
 "group_by":["queue"],"interval":"1m","range":{"last":"6h"}}
```

| Requirement | Metric | Definition | Default view |
| --- | --- | --- | --- |
| Total tasks over time by terminal status | `run.count` | Runs reaching a terminal state per interval, grouped by `status` | Stacked bars: succeeded, failed, retried, revoked |
| Error rate | `run.error_rate` | failed ÷ (succeeded + failed) per interval. Retries are excluded from the denominator; a retry that later succeeds is not an error | Line, with the alert threshold drawn on it |
| Execution time spread, global | `run.duration` | Worker-measured run time; aggregations p50, p75, p95, p99, max, histogram | Heatmap of the log-scale histogram over time, p50/p95 lines on top |
| Execution time spread, by task type | `run.duration` grouped by `task_name` | Same, per task type | Box-and-whisker per task type (p5–p95 whiskers), sorted by p95 |
| Slowest tasks | `run.list` sorted by `duration desc` | Individual runs, not aggregates, with tags and worker | Table on each task type page; global top 50 |
| Queue wait time per queue | `run.wait_time` grouped by `queue` | started_at − enqueued_at; runs without an enqueue timestamp are excluded and counted | Line per queue, p95 by default |
| Queue depth | `queue.depth` | Latest broker probe sample per interval (max within interval), else the estimate | Line per queue, area for total |
| Stale tasks | `run.stale` | Runs in `started` with no terminal event or heartbeat for longer than the task type's threshold | Count tile + live list |
| Lost tasks | `run.lost` | Runs in `started` whose worker has missed 3 heartbeats | Count tile + live list |
| Throughput (supporting) | `run.rate` | Terminal runs per second | Sparkline in the task list |

### Stale thresholds

Each task type gets a stale threshold: an explicit value set in the UI or API, else the SDK-declared `soft_time_limit`, else 3 × its 7-day p99 run time with a 5-minute floor. Queued-too-long is not a stale run; it is the wait-time metric, alerted on per queue.

### Tag aggregation

Any metric can filter by any tag (`tag.<key>`). Grouping by a tag (`group_by: ["tag.tenant"]`) is served from `task_stats_tag_1m` when the key is promoted, and from raw runs (limited to 7 days, top 20 values plus "other") when it is not. Promoting a key applies from that point on; there is no backfill in v1.

## Alerting and integrations

An alert rule is a `MetricQuery` plus a condition, evaluated every 30 seconds by the worker role. Anything that can be charted can be alerted on, including queue depth and wait time per queue, error rate per task type, and stale counts per tenant.

### Rule model

```yaml
name: Chat queue backing up
query: {metric: run.wait_time, aggregation: p95, filters: {env: prod}, group_by: [queue], interval: 1m}
warning:  {op: ">", value: 30s}
critical: {op: ">", value: 120s}
resolve_below: 20s        # hysteresis, avoids flapping
for: 3m                   # must hold this long before firing
renotify_every: 30m
channels: [slack:#ocs-alerts, instatus:chat-component]
```

`group_by` makes one alert instance per series, so a single rule watches every queue and names the one that breached. Rules are editable in the UI, via the API, and as YAML files loaded from a directory at startup ("alerts as code"), with a source flag so the UI shows file-managed rules read-only.

### Alert lifecycle

Each instance moves `ok → pending → firing → resolved → ok`. It enters `pending` when the condition first holds, `firing` once it has held for `for`, and `resolved` when the value drops below `resolve_below` for one full interval. Pending instances that recover return to `ok` silently. Every transition is written to `alert_events`, which feeds the alert history view and makes notifications replayable. A rule can be muted for a time window; muting suppresses notifications, not evaluation.

### Notifiers (built-in plugins)

| Notifier | Delivery | Behaviour |
| --- | --- | --- |
| Slack | Bot token (preferred) or incoming webhook | Posts on firing with value, threshold, a link to the pre-filtered chart, and the top 3 contributing task types; updates the same message thread on escalation and resolution (bot token only) |
| Instatus | Instatus REST API with a page API key | Maps a rule to an Instatus component: firing warning → degraded performance, firing critical → partial outage, resolved → operational. Optionally opens and resolves an incident. Never posts publicly without an explicit per-rule opt-in |
| Generic webhook | HTTP POST, HMAC-signed JSON | Stable, versioned payload; the integration point for PagerDuty, Opsgenie, n8n, and anything else |
| Email | SMTP | Digest-friendly; optional |

Delivery is at-least-once with retries and a dead-letter view in the UI. A "send test" button exists for every channel.

### Pull-based integrations

Monitoring systems that poll rather than receive pushes get two endpoints:

- `GET /metrics` (Prometheus format, token-protected): per project, queue, and task type counters, gauges, and histograms for Grafana and existing Prometheus alerting. Label cardinality is capped and promoted tags are opt-in labels.
- `GET /status/v1/<status token>`: a per-project health document (`operational`, `degraded`, `outage`, with the firing rules) designed for status-page monitors such as Instatus, Better Stack, or Uptime Kuma, which can poll it as an HTTP keyword or JSON check.

## Access model

One install is one organisation. Users see only the projects they have been invited to; instance admins see everything. There are no teams, plans, or quotas.

| Role | Scope | Can |
| --- | --- | --- |
| Instance admin | Install | Create projects, manage all users, configure SSO and instance settings. The first user to sign up becomes admin; later sign-ups need an invite |
| Project admin | Project | Invite and remove members, manage ingest keys, integrations, promoted tags, alert rules |
| Project member | Project | View everything in the project, create dashboards and personal alert rules, resolve or ignore error groups |
| Project viewer | Project | Read-only access, for stakeholders |

### Invites

A project admin invites by email with a role. The invite is a single-use, 7-day token. With SMTP configured it is emailed; without it, the UI shows a copyable link, so the install works with no mail server. Accepting an invite as an existing user adds the membership; otherwise it creates the account.

### Authentication and credentials

- Email and password (argon2id) built in; OIDC (Google, Okta, Keycloak, GitHub) as an auth-provider plugin, with optional auto-join to projects by email domain.
- Browser sessions use HTTP-only cookies with CSRF protection.
- **Personal API tokens** act as the user, optionally scoped read-only or to listed projects.
- **Ingest keys** belong to a project and can only write events. They are safe to ship in application config and can be rotated with an overlap window.
- Every administrative action is written to `audit_log`.

Authorisation lives in one place: `identity.Authorize(principal, action, project)`. Handlers call it; no other module checks roles. A test enumerates every OpenAPI operation and fails if any lacks a declared permission.

## API design

The OpenAPI 3.1 document in `api/openapi.yaml` is the source of truth. Server interfaces (oapi-codegen, strict mode) and the TypeScript client (openapi-typescript + openapi-fetch) are generated from it, so the backend cannot drift from the contract and the UI cannot call an endpoint that does not exist.

### Conventions

- Versioned path prefix `/api/v1`; breaking changes need `/api/v2`, enforced in CI by an OpenAPI diff (oasdiff) against the last release.
- Resources are nested under projects: `/api/v1/projects/{project}/...`, where `{project}` accepts the slug or ID.
- Cursor pagination (`?cursor=&limit=`), RFC 9457 problem-details errors, ISO 8601 timestamps in UTC, durations in milliseconds.
- One filter grammar everywhere, shared by the UI search bar and the API: `task:apps.chat.* status:failed queue:chat tag.tenant:acme duration:>5s`.
- Long-running list endpoints support Server-Sent Events (`Accept: text/event-stream`) for live updates; the UI uses this for the live run list and stale tasks.

### Endpoint map

| Area | Endpoints |
| --- | --- |
| Metrics | `POST /metrics/query` (one or more `MetricQuery`), `GET /metrics/catalogue` |
| Task types | `GET /task-types` (the grouped list with stats), `GET /task-types/{name}`, `PATCH /task-types/{name}` (stale threshold, notes) |
| Runs | `GET /runs` (filterable, sortable), `GET /runs/{task_id}` (attempts + event timeline), `GET /runs/stale`, `GET /runs/lost` |
| Queues | `GET /queues`, `GET /queues/{name}` |
| Errors | `GET /error-groups`, `GET /error-groups/{fp}`, `PATCH /error-groups/{fp}` (resolve, ignore, assign) |
| Workers | `GET /workers` |
| Dashboards | CRUD on `/dashboards`; definitions are plain JSON and round-trip through export and import |
| Alerts | CRUD on `/alert-rules`; `GET /alerts` (active instances); `GET /alert-events`; `POST /alert-rules/{id}/test` |
| Integrations | CRUD on `/integrations`; `POST /integrations/{id}/test` |
| Access | `/projects`, `/projects/{p}/members`, `/projects/{p}/invites`, `/projects/{p}/ingest-keys`, `/me/tokens`, `/users` (admin) |
| Ingest | `/ingest/v1/events`, `/ingest/v1/queue-samples` (separate prefix, separate auth) |

The docs site renders the spec as an interactive reference, and a `gumption` CLI (generated client + a thin command layer) covers the same operations for scripting and for AI agents operating the system.

## Frontend

The UI is organised around one question: "what's wrong, and where?" The landing page answers it at a glance, and every number on it is a link into a pre-filtered view. It is a React SPA served by the binary, using only the public API.

### Principles

- **Calm by default, loud when it matters.** Neutral greys when healthy; colour appears only for warning and critical states, so a red element always means something.
- **Everything is a filter.** Clicking a queue, task type, tag value, or chart bar adds it to the filter bar; the URL holds the full state, so any view can be shared or bookmarked.
- **Fast feels fun.** Live updates over SSE, optimistic interactions, and keyboard-first navigation: `⌘K` command palette, `/` to search, `g q` for queues, `j`/`k` through lists.
- **Delight in small doses.** Friendly empty states ("All queues are clear. Nothing waiting longer than 2s."), a subtle pulse on live counters, satisfying transitions. Nothing that slows a person who is mid-incident.
- Light and dark themes, WCAG 2.2 AA contrast, colour-blind-safe status palette with icons as well as colour.

### Screens

| Screen | What it shows |
| --- | --- |
| Project overview | Health strip (firing alerts, stale, lost); tiles for throughput, error rate, p95 wait, total depth; runs by terminal status; wait time and depth per queue; duration heatmap |
| Task types (the Sentry-style list) | One row per task type: name, sparkline of runs, run count, error rate, p50/p95 duration, p95 wait, last seen, stale count. Sort by any column; filter by queue, env, tag. Failing or slowing types float to the top in "needs attention" sort |
| Task type detail | Runs by status, duration box plot and heatmap, slowest runs table, recent failures grouped by error, breakdown by promoted tag (e.g. which tenants are slow), stale threshold setting |
| Runs explorer | Searchable, live-updating run list using the filter grammar; run detail shows attempts, event timeline, tags, worker, error and stack trace |
| Queues | Per-queue depth and wait time, with the workers consuming each queue |
| Errors | Error groups with counts, first and last seen, affected tenants; resolve, ignore, assign |
| Stale and lost | Live list of stuck runs, oldest first, with how long past threshold |
| Dashboards | Built-in overview plus custom dashboards: a grid of panels, each a `MetricQuery` built in a visual editor with a "view JSON" toggle |
| Alerts | Active alerts, rule list and editor with a live preview chart showing the threshold against the last 24 h, history |
| Settings | Members and invites, ingest keys with copy-paste SDK snippets, integrations, promoted tags, personal tokens |

### Onboarding

A new project opens on a setup page with the ingest key embedded in copy-ready snippets for Celery and the generic SDK, plus a "waiting for first event" indicator that turns into a link to the overview once data arrives. `gumption sim` can fill a demo project with realistic synthetic traffic, so the UI can be explored before any integration.

## Plugin architecture

Plugins are compiled-in Go implementations of small, stable interfaces, registered by name and selected by configuration. Out-of-process extension uses the webhook notifier and the public API. Go's native `plugin` package is not used: it is brittle across builds and does not work on every platform.

### Extension points

| Port | Interface (abridged) | Built-in implementations |
| --- | --- | --- |
| `Notifier` | `Validate(cfg) error`; `Send(ctx, Notification) (DeliveryRef, error)`; `Update(ctx, ref, Notification) error` | Slack, Instatus, webhook, email |
| `BrokerProbe` | `Queues(ctx) ([]string, error)`; `Depth(ctx, queues) (map[string]int64, error)` | Redis, RabbitMQ, SQS |
| `IngestDecoder` | `Decode(r io.Reader) iter.Seq2[domain.Event, error]` | Gumption NDJSON v1; Celery event-stream listener; OTLP (community plugin, D-005) |
| `AuthProvider` | `Begin(w, r)`; `Complete(r) (Identity, error)` | Password, OIDC |
| `EventStore` | `Write(ctx, []Event)`; `Query(ctx, MetricQuery) (Series, error)`; `ListRuns(ctx, RunListQuery) (Page, error)` | ClickHouse |
| `SecretStore` | `Get(ctx, ref) ([]byte, error)` | Env-key encryption in Postgres; Vault (later) |

### Contract for every plugin

1. Lives in its own package under `plugins/<port>/<name>/`, importing only `domain`, `platform`, and its port.
2. Registers itself in an `init()` with `registry.Register(port, name, factory)`, and is pulled into the build by one import line in `cmd/gumption/plugins.go`. A build tag can exclude it.
3. Declares its configuration as a Go struct with JSON Schema tags; the UI renders the settings form from that schema, so a new notifier needs no frontend code.
4. Passes the port's shared conformance suite (`porttest.RunNotifierSuite(t, factory)` and equivalents), which covers timeouts, retries, error classification, and secret redaction in logs.
5. Ships a docs page generated from its schema plus a hand-written setup guide.

SDK integrations follow the same idea on the client side: the core SDK owns buffering, transport, and the event schema; framework integrations (Celery, RQ, Dramatiq, BullMQ) only translate framework hooks into events.

## Tech stack

The stack favours tools with strict compilers, generated contracts, fast feedback loops, and a large body of conventional code that models write well. Where performance and AI-suitability conflict, the choice is explicit below.

| Layer | Choice | Why (performance) | Why (AI build suitability) |
| --- | --- | --- | --- |
| Server language | Go | Low memory, high-throughput HTTP, single static binary, easy horizontal scale | Small language, one formatter, fast compiles (seconds), explicit errors; models produce idiomatic Go reliably and the compiler catches most mistakes |
| Event store | ClickHouse | Columnar compression, incremental materialized views, native quantile and histogram states; billions of rows on one node | SQL; query builder output is easy to golden-test |
| Metadata store | PostgreSQL + sqlc + goose migrations | Mature, transactional, advisory locks for leader election | sqlc turns hand-written SQL into typed Go; schema errors fail at generate time, not runtime |
| API contract | OpenAPI 3.1 + oapi-codegen (strict server) | No reflection-heavy framework in the hot path | The spec is the single contract an agent edits first; server stubs and the TS client regenerate from it |
| HTTP | net/http (Go 1.22+ routing) + chi middleware | Minimal overhead | Few abstractions to learn or misuse |
| Frontend | React 19, TypeScript (strict), Vite, TanStack Router + Query | Code-split SPA, cached queries, served as static files from the binary | The most heavily represented UI stack in training data; strict types and generated API client catch integration errors at compile time |
| UI components | Tailwind CSS + shadcn/ui (Radix primitives) | Small CSS output, accessible primitives | Components are copied into the repo as plain code the agent owns and edits, not a black-box library |
| Charts | Apache ECharts | Canvas rendering handles 100k+ points; heatmaps and box plots built in | Declarative option objects are easy to generate and snapshot-test |
| SDKs | Python first (sync + asyncio), then Node and Go | Background flush thread, bounded buffer | Thin and table-driven; conformance suite defines correctness |
| Tooling | mise for tool versions, `just` for tasks, Docker Compose for dev deps | n/a | One command for every workflow (`just check`), identical on laptops, CI, and agent sandboxes |

### Alternatives considered

- **Python/Django** would match the team's existing skills and Celery's ecosystem. Rejected for the server because ingest throughput and the single-binary deployment matter, and because Go's compiler gives an AI-owned codebase stronger guardrails than Python's optional typing. The SDKs stay in Python.
- **Rust** would be faster still but compiles slowly and is harder for models to get right on the first pass; the slower edit-compile loop works against agent productivity.
- **TypeScript end to end** (Node server) would share types with the UI, but generated clients from OpenAPI already give that benefit without Node's runtime overhead on ingest.
- **HTMX + Alpine.js** keeps the UI server-rendered and simple, but would create a second, private interface beside the API. An API-native product is better served by a client of its own public API.
- **TimescaleDB instead of ClickHouse** would mean one database to run. It backs the v1 "lite" `EventStore` for small installs (D-003); ClickHouse remains the default for its rollup and quantile performance.

## AI ownership and guardrails

AI agents write and maintain the code; humans own the contracts, review the risky parts, and set direction. Guardrails are mechanical wherever possible: a rule an agent can break without CI failing is treated as a suggestion, not a rule.

### What humans own vs what agents own

| Humans approve (CODEOWNERS required review) | Agents own (CI green + automated review is enough) |
| --- | --- |
| `api/openapi.yaml`, `schema/event.v1.json`, `MetricQuery` definitions | Handlers, services, adapters behind those contracts |
| SQL migrations (Postgres and ClickHouse) | Queries, query builders, rollup readers |
| `internal/identity`, auth plugins, secret handling | UI screens, components, charts |
| Architecture rules (`.go-arch-lint.yml`, dependency-cruiser config), CI config | Plugins that pass their conformance suite |
| ADRs in `docs/adr/` | Docs pages, examples, changelog entries |

### Repository layout

```
cmd/gumption/          single binary entrypoint, plugin imports
internal/<module>/     one module per row in the Architecture table
  port.go              the module's public interface
  AGENTS.md            purpose, invariants, allowed imports, how to test
plugins/<port>/<name>/ compiled-in plugins
api/openapi.yaml       API contract (source of truth)
schema/                event JSON Schema, SQL migrations
web/                   React app (web/src/features/<screen>/)
sdk/python/            core SDK + gumption-celery
docs/                  docs site, ADRs, runbooks
AGENTS.md              repo map, commands, rules for agents (CLAUDE.md symlinks here)
```

Every module carries its own `AGENTS.md`, kept under 150 lines, stating what the module is for, its invariants (e.g. "merge rules must stay commutative"), what it may import, and which tests prove it works. An agent working on one module reads that file and `port.go` and should not need the rest of the codebase.

### Mechanical guardrails (all run by `just check` and in CI)

1. **Boundaries:** go-arch-lint enforces the import table; dependency-cruiser enforces that `web/src/features/*` do not import each other and only call the generated API client.
2. **Types and lint:** golangci-lint with a strict preset (errcheck, gosec, exhaustive switches, no naked goroutines outside `platform`), TypeScript `strict` with `noUncheckedIndexedAccess`, ESLint banning `any` and non-null assertions.
3. **Generated code is never hand-edited:** CI regenerates OpenAPI stubs, the TS client, and sqlc code, and fails on any diff.
4. **Contract compatibility:** oasdiff blocks breaking API changes; the event schema has a compatibility test against recorded fixtures from every released SDK version.
5. **Tests by layer:** unit tests on `domain` (with property-based tests for merge rules and percentiles), golden-file tests for every generated ClickHouse query, integration tests against real Postgres and ClickHouse via testcontainers, plugin conformance suites, and Playwright end-to-end tests that drive the UI against `gumption sim` data.
6. **Coverage floors per module:** 90% for `domain`, `query`, `alerting`, `identity`; 70% elsewhere. Coverage may not drop on a PR.
7. **Performance gates:** benchmark suite for ingest throughput and the top 10 dashboard queries on a fixed dataset; a regression over 15% fails the build.
8. **Security:** govulncheck, npm audit, gitleaks secret scanning, and a test that every API operation declares a permission.
9. **Size limits:** files over 500 lines and functions over 80 lines fail lint, keeping each unit small enough to reason about in one context window.
10. **Docs drift:** a PR that changes the OpenAPI spec, a plugin schema, or a config key must touch the matching docs page; CI checks the pairing.

### Working loop for agents

Each task starts from an issue with acceptance criteria. The agent changes the contract first if needed (and stops for human approval when it does), regenerates, implements behind the port, adds tests, updates docs, and opens a PR that a second agent reviews against the module's `AGENTS.md` before a human sees it. `gumption sim` plus Playwright screenshots let an agent verify UI work visually rather than claiming it works. Architecture changes are proposed as ADRs, never made silently in code.

## Deployment, operations, documentation

The default install is `docker compose up` with three containers: `gumption`, `postgres`, `clickhouse`. A Helm chart covers Kubernetes, with separate Deployments per role (`ingest` scaled by HPA on request rate, `api`, and `worker`) and the option to point at managed Postgres and ClickHouse.

### Operations

- **Configuration:** a single YAML file with every key overridable by `GUMPTION_*` environment variables; `gumption config validate` checks it and prints the effective config with secrets redacted.
- **Migrations:** applied automatically at startup behind an advisory lock, or by `gumption migrate` for controlled rollouts. Forward-only; every migration is tested against a snapshot of the previous release's schema.
- **Self-observability:** Gumption exposes its own Prometheus metrics (ingest rate, batch latency, dropped events, evaluator lag, notifier failures), structured JSON logs, and `/healthz` and `/readyz` endpoints.
- **Retention:** per-table TTLs set from config; `gumption storage usage` reports size per project and table.
- **Backups:** documented recipes for `pg_dump` and ClickHouse `BACKUP`; Postgres holds everything that cannot be regenerated, so it is the one that matters most.
- **Releases:** semantic versioning, signed multi-arch images, SBOM attached, changelog generated from conventional commits.
- **Licence:** Apache-2.0 (decided: D-001).

### Documentation plan

Docs live in `docs/` and build into a static site (Astro Starlight) on every merge. Nothing ships without its docs page, enforced by the docs-drift check.

| Section | Contents | Generated or written |
| --- | --- | --- |
| Getting started | Compose install, first project, Celery in 5 minutes | Written |
| Guides | Tags and tenants, alert recipes (queue backing up, error spike), Instatus setup, Slack setup, Kubernetes install, upgrading | Written |
| Concepts | Runs and events, merge rules, metrics catalogue definitions, stale vs lost | Written |
| API reference | Every endpoint with examples | Generated from OpenAPI |
| Event protocol | Wire format, versioning, writing a new SDK | Schema generated; guide written |
| SDK reference | Python API, Celery options | Generated from docstrings |
| Plugins | One page per plugin, settings table | Generated from config schema + written setup notes |
| Configuration reference | Every config key, default, env var | Generated from the config struct |
| Architecture | Module map, ADRs, AGENTS.md index | Written, reviewed by humans |
| Operations | Sizing, backups, retention, troubleshooting runbooks | Written |

## Milestones, risks, open questions

Delivery runs in five milestones, each ending at a gate that a real pilot project has to pass. Contracts and guardrails come first (M0), because an AI-owned codebase without them drifts from the first commit.

| Milestone | Scope | Exit gate |
| --- | --- | --- |
| M0 Foundations | Repo skeleton, contracts, CI guardrails, AGENTS.md files, gumption sim | `just check` runs every guardrail on a sample module |
| M1 Ingest, metrics | Ingest, ClickHouse schema, Python SDK, gumption-celery, task list, overview | A pilot project sends events; sim meets ingest targets |
| M2 Queues and tags | Broker probes, wait time, stale and lost, promoted tags, runs explorer | One week of pilot production data with no dropped events |
| M3 Alerts | Alert rules, Slack, Instatus, webhooks, /metrics, /status, invites, roles | Pilot on-call relies on Gumption alerts for queue health |
| M4 Version 1.0 | Custom dashboards, error groups, OIDC, Helm chart, Node SDK, docs site | Docs complete, upgrade from M3 tested, public 1.0 release |

M1 alone replaces Flower for a Celery team; each later milestone is independently useful. Durations are left open until M0 shows the agent team's real throughput.

### Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| ClickHouse is heavy for small installs | Adoption friction; ops burden | Tuned low-memory config in Compose; `EventStore` port keeps a TimescaleDB lite mode possible |
| Tag cardinality explodes (e.g. user IDs as tags) | Rollup tables and `/metrics` grow without bound | Promotion limited to 5 keys; per-key cardinality cap with an "other" bucket; warnings in the UI |
| Clock skew corrupts wait times | Misleading wait-time alerts | Server receive time recorded; skew warning per project; durations use monotonic clocks |
| SDK overhead or failure affects the monitored app | Loss of trust; outages blamed on Gumption | Bounded buffers, background flush, drop-not-block, overhead benchmark in CI (target under 50 µs per event) |
| Architecture erodes under many agent PRs | Harder changes, more bugs | Import rules enforced in CI, human-owned contracts, ADRs, size limits |
| Celery signal behaviour differs across versions and pools (prefork, gevent, threads) | Missing or duplicate events | Conformance matrix across supported Celery versions and pool types |

### Open questions

None open.

Resolved (answers recorded in `DECISIONS.md`):

- Name: Gumption, renamed from the working name "Conveyor" after a collision check (D-002).
- Licence: Apache-2.0 (D-001).
- Lite single-database mode: included in v1 as a PostgreSQL/TimescaleDB `EventStore`; ClickHouse stays the default (D-003).
- Worker actions: none; Gumption stays read-only (D-004).
- OTLP ingest: left to a community plugin on the `IngestDecoder` port; not a core feature (D-005).
- Pilot: open-chat-studio; gate reviewer: snopoke (D-006).
- Celery matrix for 1.0: Celery 5.3, 5.4, 5.5 × prefork, threads, gevent, solo on Python 3.10–3.13; eventlet is not supported (D-007).
