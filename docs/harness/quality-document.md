# Quality document

Codebase health by product domain and architectural layer. The evaluator
rubric asks "was this PR good?"; this document asks "is the project getting
stronger or weaker?". The gardener updates it after each milestone and every
~10 merged features.

**Grades:** A: verification passing, clean boundaries, agent-legible, stable
tests. B: passing, minor gaps. C: partly working or hard for agents to
understand. D: not working or structurally unsound. `-` means not built yet.

## Product domains

| Domain | Grade | Verification | Agent legibility | Test stability | Key gaps | Last updated |
| --- | --- | --- | --- | --- | --- | --- |
| Ingest and protocol | - | - | - | - | - | - |
| Run stitching and storage | - | - | - | - | - | - |
| Metrics and query | - | - | - | - | - | - |
| Queues, stale, lost | - | - | - | - | - | - |
| Tags | - | - | - | - | - | - |
| Alerting and notifiers | - | - | - | - | - | - |
| Access and identity | - | - | - | - | - | - |
| Web UI | - | - | - | - | - | - |
| Python SDK and Celery | - | - | - | - | - | - |
| Docs | - | - | - | - | - | - |

## Architectural layers

| Layer | Grade | Boundary enforcement | Agent legibility | Key gaps | Last updated |
| --- | --- | --- | --- | --- | --- |
| platform | - | - | - | - | - |
| domain | - | - | - | - | - |
| ingest | - | - | - | - | - |
| eventstore | - | - | - | - | - |
| metastore | - | - | - | - | - |
| query | - | - | - | - | - |
| identity | - | - | - | - | - |
| alerting | - | - | - | - | - |
| notify | - | - | - | - | - |
| probes | - | - | - | - | - |
| api | - | - | - | - | - |
| web | - | - | - | - | - |
| plugins | - | - | - | - | - |

## Harness

| Component | Still needed? | Last simplification test | Notes |
| --- | --- | --- | --- |
| Root AGENTS.md workflow | yes | - | - |
| feature_list.json + check_harness.py | yes | - | - |
| Per-module AGENTS.md | yes | - | - |
| Reviewer agent | yes | - | - |

## Change history

### 2026-11-26

- Harness created; no product code yet. All grades `-`.
