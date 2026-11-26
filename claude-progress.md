# Progress Log

Read the Current Verified State at the start of every session; update it and
add a session entry before you stop. (The filename is a harness convention; any
agent uses it.)

## Current Verified State

- Repository root: repository checkout root (contains `AGENTS.md`)
- Standard startup path: `./init.sh`
- Standard verification path: `./scripts/verify.sh` (becomes `just check` after m0-001)
- Features passing: 0 / 54
- Current highest-priority unfinished feature: m0-001 Go module, binary entrypoint, mise + just
- Current blocker: none. Open human decisions D-001 to D-010 all have defaults; none blocks M0.

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
