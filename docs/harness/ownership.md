# Ownership: what needs a human

From `docs/design.md` → AI ownership and guardrails. `.github/CODEOWNERS`
encodes the left column so GitHub requests the human's review automatically.

| Humans approve (CODEOWNERS review required) | Agents own (green CI + reviewer-agent Accept is enough) |
| --- | --- |
| `api/openapi.yaml`, `schema/event.v1.json`, MetricQuery definitions | Handlers, services, adapters behind those contracts |
| SQL migrations (`schema/postgres/`, `schema/clickhouse/`) | Queries, query builders, rollup readers |
| `internal/identity/`, auth plugins, secret handling | UI screens, components, charts |
| Architecture rules (`.go-arch-lint.yml`, dependency-cruiser config), CI config (`.github/`), lint configs | Plugins that pass their conformance suite |
| ADRs in `docs/adr/` | Docs pages, examples, changelog entries |
| The harness itself: `AGENTS.md`, `docs/design.md`, `docs/harness/`, `scripts/check_harness.py` | Progress log, handoff, feature state and evidence |

Also human-only, regardless of path:

- Anything public or irreversible: releases, publishing packages or images,
  making the repo public, the licence, the product name.
- Creating accounts, buying anything, adding secrets or credentials.
- Confirming milestone gates that depend on a pilot (D-006).
- Repository settings (branch protection, apps, secrets).

Agents **can** and should, without asking: choose libraries within the
design's stack, structure code inside a module, write and refactor tests, fix
bugs, improve docs, split features into smaller ones in `feature_list.json`
(keeping the parent's verification), and record decisions in the progress log.

When a feature needs both kinds of change, split the PR: contract or
migration first (human review), implementation second (agent review).

## Who merges

- A PR that touches only the right column: the builder merges it, after green
  CI and a reviewer-agent Accept recorded in the PR description.
- A PR that touches anything in the left column: the human merges it. Agents
  mark it ready and stop; they never merge, approve, or auto-merge it.
- The bookkeeping files (progress log, handoff, feature state, `DECISIONS.md`)
  travel in the feature's PR, never in a PR of their own while a feature PR is
  open.
