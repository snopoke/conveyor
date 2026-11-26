# AGENTS.md

Gumption is a self-hosted observability service for background task queues
(Celery first, any queue through an SDK): one Go binary, PostgreSQL for
metadata, ClickHouse for events, and a React UI that uses only the public API.

**This repository is built and maintained by AI agents.** A human owner sets
direction and decides only what agents cannot. Your job is to leave the repo in
a state where the next agent session can continue without guessing and without
asking a human anything that the repo already answers.

`CLAUDE.md` is a symlink to this file. Every module under `internal/` has its
own `AGENTS.md`; read it before touching that module.

## Where things are

| Path | What it is |
| --- | --- |
| `docs/design.md` | The product and architecture design. The source of truth for *what* to build. |
| `feature_list.json` | The backlog and the source of truth for feature state. |
| `claude-progress.md` | Session log and the current verified state. Read first, write last. |
| `session-handoff.md` | Compact handoff from the most recent session. |
| `DECISIONS.md` | The human decision queue. Each open entry has a `needs-human` GitHub issue where the human answers. |
| `docs/harness/` | How agents work here: ownership, review rubric, quality grades, checklists. |
| `docs/adr/` | Architecture decision records. Architecture changes are proposed here, never made silently in code. |
| `init.sh` | Standard startup and verification path. |
| `scripts/verify.sh` | Standard verification path (`just check` once it exists). |

Planned code layout (created during M0; see `docs/design.md` → Repository
layout): `cmd/gumption/`, `internal/<module>/` (each with `port.go` and
`AGENTS.md`), `plugins/<port>/<name>/`, `api/openapi.yaml`, `schema/`, `web/`,
`sdk/python/`, `docs/`.

## Startup workflow

Before writing code:

1. `pwd` — confirm you are at the repository root.
2. Read `claude-progress.md` (Current Verified State) and `session-handoff.md`.
3. Read `DECISIONS.md`, then the owner's comments on open `needs-human`
   GitHub issues. Record and apply new answers before other work (the
   procedure is at the top of `DECISIONS.md`).
4. `git log --oneline -10`.
5. Run `./init.sh`. If baseline verification fails, fixing it **is** your task.
   Do not stack new work on a broken baseline.
6. Pick a feature: the lowest `priority` number in `feature_list.json` whose
   status is `not_started`, whose `depends_on` are all `passing`, and whose
   `human_gate` is not waiting on an open decision. If a feature is already
   `in_progress` with your branch as `owner`, resume it instead.
7. Set it to `in_progress`, set `owner` to your branch name, and commit that
   change before you start.

## Working rules

- One feature per session. Stay inside its scope; a narrow supporting fix for
  a blocker is allowed and must be noted in the progress log.
- Contract first: if the feature changes `api/openapi.yaml`,
  `schema/event.v1.json`, MetricQuery definitions, or SQL migrations, change the
  contract first, regenerate, then implement behind the port.
- Never hand-edit generated code. Regenerate it.
- Never weaken, skip, or delete a test, lint rule, coverage floor, or
  verification step to make work look complete. Never rewrite
  `feature_list.json` to hide unfinished work.
- Follow the import rules in `docs/design.md` → Modules and boundaries. If a
  rule is in your way, write an ADR proposal; do not work around it.
- Prefer durable repo artifacts (tests, ADRs, docs, the progress log) over
  chat summaries. Anything not in the repo is lost when your session ends.
- Verify UI work visually (Playwright screenshots against `gumption sim`
  data), not by assertion that it works.

## Decide or escalate

Default to deciding. Record non-obvious choices in the progress log, or in an
ADR when they affect architecture. Escalate to the human **only** when the
choice:

1. changes a human-owned path (see `docs/harness/ownership.md`),
2. needs money, credentials, accounts, or access the repo does not have,
3. is public or irreversible (release, package publish, licence, naming), or
4. is a product or strategy question that `docs/design.md` does not settle.

To escalate: add an entry to `DECISIONS.md` using its template, with options,
your recommendation, and a **reversible default** you will follow meanwhile,
and open its `needs-human` GitHub issue so the human is notified. Never ask
the human in PR comments, other issues, or chat.
If a safe default exists, keep working on it. If none exists, set the feature
to `blocked`, reference the decision ID in `notes`, and move to the next
unblocked feature. Never stop the session just to wait for an answer.

## Definition of done

A feature moves to `passing` only when all are true:

- the behaviour in `user_visible_behavior` is implemented;
- every step in its `verification` list actually ran and passed;
- evidence (commands run, test names, screenshot paths, PR link) is recorded
  in the feature's `evidence` array;
- `./init.sh` still passes from a clean checkout;
- docs touched by the change are updated (API, config, plugin, or concept page);
- the PR was reviewed by a second agent against `docs/harness/evaluator-rubric.md`
  with verdict **Accept**, and any human-owned path has human approval.

## Pull requests

- Branch per feature. Conventional commit messages (`feat(ingest): ...`).
- Fill in `.github/pull_request_template.md`, including the feature ID and the
  evidence.
- PRs that touch only agent-owned paths merge on green CI plus a reviewer-agent
  **Accept**. PRs that touch human-owned paths wait for the human (CODEOWNERS).

## End of session

Run through `docs/harness/clean-state-checklist.md`, then:

1. Update `claude-progress.md` (Current Verified State and a new session entry).
2. Update the feature's `status`, `evidence`, and `notes` in `feature_list.json`.
3. Overwrite `session-handoff.md` for the next session.
4. Record unresolved risks; add any new human questions to `DECISIONS.md`.
5. Commit and push once the repo is in a safe state. Leave `./init.sh` green.
