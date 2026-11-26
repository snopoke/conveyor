# How agents build Conveyor

The harness is the set of files, checks, and habits that let a sequence of
agent sessions build Conveyor without a human in the loop for routine work. It
follows the templates in
[learn-harness-engineering](https://github.com/walkinglabs/learn-harness-engineering/tree/main/docs/en/resources/templates),
adapted to the design in `docs/design.md`.

## Principles

1. **The repo is the memory.** A session knows only what is in the repo.
   Progress, decisions, and evidence live in files, not in chat.
2. **Rules are mechanical.** A rule an agent can break without CI failing is a
   suggestion. Every rule that matters gets a check (`scripts/check_harness.py`
   today; the M0 guardrails next) and a canary proving the check fires.
3. **One feature per session, verified before it counts.** `passing` means
   the verification steps ran and the evidence is recorded.
4. **Humans own contracts and direction; agents own everything behind them.**
   See `ownership.md`.
5. **Ask rarely, never block.** Escalations go to `DECISIONS.md` with a
   reversible default so work continues.

## Roles

| Role | Started by | Does |
| --- | --- | --- |
| Builder | schedule or human | Runs the startup workflow in `AGENTS.md`, takes the next feature, opens a PR. |
| Reviewer | a builder's PR | A *separate* session reviews the PR against `evaluator-rubric.md` and the touched modules' `AGENTS.md`. It never reviews its own work. Posts Accept, Revise, or Block with reasons. |
| Gardener | every ~10 merged features, or when quality grades drop | Updates `quality-document.md`, removes dead code and stale docs, proposes harness simplifications, re-tunes the rubric. Does not add features. |
| Human owner | `DECISIONS.md`, CODEOWNERS review requests | Answers decisions, approves PRs on human-owned paths, confirms milestone gates. |

## The loop

```
pick feature ─▶ contract first? ──yes──▶ edit contract, regenerate ─┐
     ▲                │ no                                          │
     │                ▼                                             ▼
     │          implement behind the port, add tests, update docs ◀─┘
     │                │
     │                ▼
     │          run verification, record evidence
     │                │
     │                ▼
     │          open PR ─▶ reviewer agent ─▶ Revise? back to builder
     │                │ Accept
     │                ▼
     │          human-owned path? ──yes──▶ wait for CODEOWNERS approval
     │                │ no
     │                ▼
     └──────── merge, update progress log + feature_list.json
```

## Files

| File | Purpose | Updated by |
| --- | --- | --- |
| `AGENTS.md` (root) | Operating rules every session follows | Human-owned; agents propose changes by PR |
| `feature_list.json` | Backlog and feature state | Builders |
| `claude-progress.md` | Current verified state + session log | Every session |
| `session-handoff.md` | Compact note for the very next session | Every session (overwritten) |
| `DECISIONS.md` | Human decision queue | Agents ask, human answers |
| `docs/harness/evaluator-rubric.md` | Review scorecard | Reviewer uses; gardener tunes |
| `docs/harness/quality-document.md` | Codebase health grades over time | Gardener |
| `docs/harness/clean-state-checklist.md` | End-of-session checklist | Every session |
| `internal/<module>/AGENTS.md` | Module purpose, invariants, imports, tests | Builders, from `module-agents-template.md` |
| `docs/adr/` | Architecture decisions | Agents propose, human approves |

## Tuning the harness

Agents are poor judges of their own work out of the box. The gardener compares
reviewer verdicts with the human's verdict on the PRs the human did review,
tightens rubric criteria where they diverge, and logs each change in
`evaluator-rubric.md` → Tuning log. Every harness component encodes an
assumption about what models cannot do; the gardener periodically removes one,
compares quality grades, and restores it only if grades drop.
