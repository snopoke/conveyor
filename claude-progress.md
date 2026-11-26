# Progress Log

Read the Current Verified State at the start of every session; update it and
add a session entry before you stop. (The filename is a harness convention; any
agent uses it.)

## Current Verified State

- Repository root: repository checkout root (contains `AGENTS.md`)
- Standard startup path: `./init.sh` (needs mise; installs the toolchain pinned in `mise.toml`)
- Product name: Gumption (binary `gumption`, module `github.com/snopoke/gumption`). The GitHub repo is still `snopoke/conveyor` until the owner renames it.
- Standard verification path: `./scripts/verify.sh` → `mise exec -- just check` (harness, gofmt, go build, vet, test)
- Features passing: 0 / 55
- m0-001: implemented and verified on `feat/m0-001-toolchain`, PR #13. Still `in_progress` until the owner approves (CI is human-owned).
- Open human decisions: none. D-001 and D-003 to D-010 decided (PR #12, merged). D-002 decided by the owner in session: rename to **Gumption** (rename PR on `chore/rename-gumption`, closes #2).
- Current blocker: none for agents. m0-002 depends on m0-001 being `passing`, so the next session should first check PR #13.

## Session Log

### Session 001

- Date: 2026-11-26
- Goal: Set up the repository for agent-built development from the design doc and the learn-harness-engineering templates.
- Completed: Markdown copy of the design at `docs/design.md`; root `AGENTS.md` (+ `CLAUDE.md` symlink); `init.sh` and `scripts/verify.sh`; `feature_list.json` with 54 features across M0–M4; `DECISIONS.md` with the design's open questions plus setup decisions; `docs/harness/` (operating model, ownership, evaluator rubric, quality document, clean-state checklist, module AGENTS.md template); ADR 0001; CODEOWNERS, PR and issue templates, CI workflow; `scripts/check_harness.py` with tests; SessionStart hook printing a brief.
- Verification run: `./init.sh` (runs `scripts/check_harness.py` and its unit tests).
- Evidence captured: `harness: ok`; 14 unit tests pass, including one canary per harness rule.
- Commits: initial harness commit on branch `sk/wizardly-cerf-dcesk4`.
- Files or artifacts updated: all of the above.
- Known risk or unresolved issue: CODEOWNERS is advisory until branch protection is enabled (D-010). No agent scheduling exists yet (D-009). The architecture diagram in `docs/design.md` is an ASCII redraw of the original.
- Next best step: m0-001.

### Session 002

- Date: 2026-11-26
- Goal: Make the human decision queue notify the owner and accept answers as GitHub issue comments.
- Completed: Created `main` from the harness commit. Opened issues #1–#10 (label `needs-human`, assigned to the owner) mirroring D-001–D-010; added an **Issue** field to every entry; documented the ask / collect-answers / follow-up procedure at the top of `DECISIONS.md`; `AGENTS.md` startup step 3 and the escalation rule now include the issues; `check_harness.py` requires open decisions to have an issue link (or `pending`).
- Verification run: `./scripts/verify.sh`.
- Evidence captured: `harness: ok`; 15 unit tests pass, including the new `test_open_decision_needs_issue` canary.
- Commits: `chore(harness): mirror decisions as needs-human issues`.
- Files or artifacts updated: `DECISIONS.md`, `AGENTS.md`, `docs/harness/README.md`, `scripts/check_harness.py`, `scripts/test_check_harness.py`, `.github/ISSUE_TEMPLATE/needs-human.yml`.
- Known risk or unresolved issue: only comments by `snopoke` count as answers; agents must check the comment author. Same open risks as Session 001 (D-009, D-010).
- Next best step: m0-001.

### Session 003

- Date: 2026-11-26
- Goal: apply the owner's decision answers, then implement m0-001.
- Completed:
  - All ten `needs-human` issues had answers from `snopoke`. D-001 and D-003 to D-010 are recorded as decided and applied on `chore/apply-decisions-d001-d010`, PR #12 (merged by the owner; closed #1 and #3 to #10). That PR adds `LICENSE` (Apache-2.0), new feature m4-010 (lite PostgreSQL/TimescaleDB EventStore, required by m4-009), gate text for D-006/D-007/D-008, and resolved open questions in `docs/design.md`.
  - D-002: the owner asked for a collision check. It was posted on issue #2 (risk medium-high; recommends renaming, with "taskscope" as the top candidate). The entry stays open.
  - m0-001 on `feat/m0-001-toolchain`, PR #13: `go.mod`, `cmd/gumption` (`version` and `help`, tested), `mise.toml`, `justfile` (`just check`), and `init.sh`/`verify.sh`/CI now run on the pinned toolchain.
- Supporting fix: `scripts/test_check_harness.py` had three canaries that assumed `features[0]` had no owner, no evidence and was not passing. They failed as soon as m0-001 went `in_progress`. Each now sets its own precondition and asserts the same rule.
- Agent decisions:
  - Module path is `github.com/snopoke/gumption`, matching the decided name. The repo URL differs until the owner renames the repo; that only matters for external `go get`.
  - Pinned versions are the latest stable releases per `mise latest`, except Python 3.13. Python 3.13 is the top of the D-007 matrix; 3.15 is too new for the SDK.
  - `init.sh` start command is `version` until a `serve` command exists.
  - `just check` also runs a gofmt check.
- Verification run: on a fresh clone, `mise install`, `go run ./cmd/gumption version`, `just check` and `./init.sh` all exit 0. Canaries (gofmt, failing test, vet, harness) each made `just check` fail. CI `verify` is green on PR #13. Details are in the m0-001 `evidence`.
- Commits (PR #13, rebuilt): `chore(features): start m0-001`, `feat(tooling): Go module, gumption binary, mise toolchain and just check`, `chore(decisions): link D-002 collision report`, `docs(progress): m0-001 evidence, session 003 log and handoff`. Also the decisions commit (PR #12) and `chore: rename the project to Gumption (D-002)` on `chore/rename-gumption`.
- Review: reviewer agent returned Revise. The main finding was that `go build ./...` had written a 2.4 MB `conveyor` binary that `git add -A` committed. Removed. The owner then authorized a force-push, so the branch was rebuilt from `main` and the binary is in no commit. Also fixed: building with `-o /dev/null`, and gitignoring `/conveyor`. Also fixed: exact Python pin, robust gofmt recipes, init.sh `mise env` failure handling, `just run` quoting, empty-stdout assertions. Lesson for agents: check `git status` before `git add -A`. Re-review: **Accept** (single 1 in Handoff, fixed).
- Known risk or unresolved issue:
  - The owner merged PR #12 before the D-002 report-link commit reached it; that commit was carried into PR #13 (cherry-pick) after merging `main`.
  - D-009 = C means sessions start only when the owner starts them.
- Next best step:
  - If PR #13 is merged or approved, set m0-001 to `passing` and start m0-002.
  - If the owner requests changes, address them on `feat/m0-001-toolchain`.
- Late in the session the owner (in chat) answered D-002: rename to Gumption, and asked for the force-push.
  - Recorded D-002 as decided.
  - Renamed docs, harness and backlog on `chore/rename-gumption`. Excluded: GitHub URLs (`snopoke/conveyor`), decision history, the progress log, and the files PR #13 owns.
  - Rebuilt PR #13 with `cmd/gumption` and module `github.com/snopoke/gumption`, then re-verified on a fresh clone.

