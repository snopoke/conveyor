# Evaluator rubric

The reviewer agent scores every PR with this rubric before merge. The reviewer
must be a different session from the builder and must read the diff, the
feature entry in `feature_list.json`, and the `AGENTS.md` of every touched
module. Score each row 0, 1 or 2 using the criteria, not overall impressions.

| Category | 2 (pass) | 1 (revise) | 0 (block) |
| --- | --- | --- | --- |
| Correctness | Every `user_visible_behavior` clause is implemented and a test exercises it. | A clause is untested or only partly implemented. | Behaviour differs from the feature or from `docs/design.md`. |
| Verification | Every `verification` step ran; `evidence` names commands, test names, screenshots, or CI run links that a reviewer can re-run. | Evidence is vague ("tests pass") or a step was substituted without a note. | A step was skipped, or evidence claims a check that did not run. |
| Scope | Changes stay within the feature, plus noted narrow supporting fixes. | Unrelated refactors or drive-by changes without a note. | Touches human-owned paths not required by the feature, or another feature's scope. |
| Guardrails | No test, lint rule, coverage floor, or check was weakened; generated code was regenerated, not edited; import rules hold. | A rule was loosened with a written justification awaiting human review. | A rule, test, or check was weakened or bypassed silently. |
| Reliability | `./init.sh` passes from a clean checkout; tests are deterministic (no sleeps, fixed seeds, no network outside testcontainers). | Flaky-looking patterns (sleep, time.Now in tests, unordered map output in golden files). | Baseline broken or a test is known flaky. |
| Maintainability | Files < 500 lines, functions < 80 lines, names match the design's vocabulary, module `AGENTS.md` updated if invariants or imports changed. | Minor gaps in docs or naming. | Module boundaries blurred, or a new concept with no doc. |
| Handoff | `claude-progress.md`, `session-handoff.md`, and the feature entry let a fresh session continue without reading chat. | Progress updated but next step unclear. | State files not updated or contradict the code. |

## Verdict

- **Accept**: all rows 2, or a single 1 in Maintainability or Handoff with the fix listed as a follow-up feature.
- **Revise**: any other 1. List each required fix as a checklist in the review.
- **Block**: any 0. Explain what must change before re-review.

The reviewer must not talk itself into Accept: if it writes down a problem,
the score reflects it.

## Review output format

```
Feature: <id>   Verdict: Accept | Revise | Block
| Category | Score | Notes |
...
Required fixes:
- [ ] ...
Missing evidence:
- ...
```

## Tuning log

Record every change to the criteria above, why, and which PRs prompted it.

- 2026-11-26: initial version adapted from the learn-harness-engineering template with Gumption-specific pass/fail criteria.
