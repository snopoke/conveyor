# ADR 0001: Agent harness for an agent-built codebase

- **Status:** accepted
- **Date:** 2026-11-26
- **Proposed by:** harness setup session

## Context
`docs/design.md` sets the goal that Gumption is built and maintained primarily
by AI agents, with humans owning contracts and direction. Agent sessions are
stateless and short; without durable state and mechanical rules, work drifts
and verification is claimed rather than performed.

## Decision
Adopt the learn-harness-engineering templates: root `AGENTS.md` (with
`CLAUDE.md` symlinked), `init.sh`, `feature_list.json`, `claude-progress.md`,
`session-handoff.md`, plus an evaluator rubric, quality document, and clean
state checklist under `docs/harness/`. Add `DECISIONS.md` as the single human
decision queue with reversible defaults, and `scripts/check_harness.py` to
enforce feature-state rules mechanically until M0 builds the full guardrails.

## Consequences
Every session pays a small startup cost (read state, run `init.sh`). The
backlog is explicit and machine-checked. The human sees questions in one file.
The harness must be pruned over time (see quality document → Harness).

## Alternatives considered
- GitHub issues as the backlog: richer UI, but not readable offline by every
  agent runtime and not checkable in CI. Issues may mirror the file later.
- No harness until code exists: the design calls for contracts and guardrails
  first (M0), and the harness is what makes M0 executable by agents.
