#!/usr/bin/env python3
"""Mechanical checks for the agent harness.

A harness rule an agent can break without CI failing is a suggestion, not a
rule. This script turns the rules in AGENTS.md about feature state, decisions,
and module docs into checks. It also caps the size of the files every session
reads, so their cost stays flat as the project grows. Standard library only.

Usage: python3 scripts/check_harness.py [repo_root]
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REQUIRED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "DECISIONS.md",
    "claude-progress.md",
    "session-handoff.md",
    "feature_list.json",
    "init.sh",
    "docs/design.md",
    "docs/harness/README.md",
    "docs/harness/ownership.md",
    "docs/harness/evaluator-rubric.md",
    "docs/harness/clean-state-checklist.md",
    "docs/harness/quality-document.md",
    "docs/harness/module-agents-template.md",
    "docs/adr/0000-template.md",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
]
STATUSES = {"not_started", "in_progress", "blocked", "passing"}
FEATURE_KEYS = {
    "id": str,
    "milestone": str,
    "priority": int,
    "area": str,
    "title": str,
    "user_visible_behavior": str,
    "status": str,
    "owner": (str, type(None)),
    "depends_on": list,
    "human_gate": (str, type(None)),
    "verification": list,
    "evidence": list,
    "notes": str,
}
MODULE_AGENTS_MAX_LINES = 150
PROGRESS_MAX_SESSIONS = 5
EVIDENCE_MAX_CHARS = 400
EVIDENCE_MAX_ITEMS = 15
FEATURE_ARCHIVE_DIR = "docs/features"
SESSION_HEADING = re.compile(r"^### Session\b", re.M)
DECIDED_LINE = re.compile(r"^- \*\*(D-\d{3})\*\* \S.*\[#\d+\]\(https://github\.com/\S+/issues/\d+\)\s*$")
DECISION_HEADING = re.compile(r"^### (D-\d{3})\b", re.M)
DECISION_STATUS = re.compile(r"^- \*\*Status:\*\* (open|decided|superseded)\b", re.M)
DECISION_REF = re.compile(r"\bD-\d{3}\b")
DECISION_ISSUE = re.compile(r"^- \*\*Issue:\*\* (https://github\.com/\S+/issues/\d+|pending)\s*$", re.M)


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f"missing required file: {rel}")

    claude = root / "CLAUDE.md"
    if claude.exists() and not (claude.is_symlink() and os.readlink(claude) == "AGENTS.md"):
        errors.append("CLAUDE.md must be a symlink to AGENTS.md")

    decisions = _decisions(root, errors)
    _features(root, decisions, errors)
    _progress(root, errors)
    _module_agents(root, errors)
    return errors


def _decisions(root: Path, errors: list[str]) -> set[str]:
    path = root / "DECISIONS.md"
    if not path.exists():
        return set()
    text = path.read_text()
    if "\n## Open" not in text or "\n## Decided" not in text:
        errors.append("DECISIONS.md: needs '## Open' and '## Decided' sections")
        return set()
    open_part = text.split("\n## Open", 1)[1].split("\n## Decided", 1)[0]
    decided_part = text.split("\n## Decided", 1)[1]

    ids = DECISION_HEADING.findall(open_part)
    sections = DECISION_HEADING.split(open_part)[1:]
    for did, body in zip(sections[::2], sections[1::2]):
        status = DECISION_STATUS.search(body)
        if not status or status.group(1) != "open":
            errors.append(f"DECISIONS.md: {did} is under Open but lacks '- **Status:** open'")
        elif not DECISION_ISSUE.search(body):
            errors.append(f"DECISIONS.md: open {did} lacks a '- **Issue:** <issue URL>|pending' line")

    for did in DECISION_HEADING.findall(decided_part):
        errors.append(
            f"DECISIONS.md: decided {did} must be a one-line entry; move the full text to docs/decisions/archive.md"
        )
    index = [ln for ln in decided_part.splitlines() if ln.startswith("- ")]
    for ln in index:
        m = DECIDED_LINE.match(ln)
        if not m:
            errors.append(f"DECISIONS.md: malformed decided line: {ln[:80]}")
        else:
            ids.append(m.group(1))
    if len(ids) != len(set(ids)):
        errors.append("DECISIONS.md: duplicate decision IDs")
    return set(ids)


def _features(root: Path, decisions: set[str], errors: list[str]) -> None:
    path = root / "feature_list.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        errors.append(f"feature_list.json: invalid JSON: {exc}")
        return
    features = data.get("features")
    if not isinstance(features, list):
        errors.append("feature_list.json: 'features' must be a list")
        return
    sources = [("feature_list.json", features)]
    archive = root / FEATURE_ARCHIVE_DIR
    for arch in sorted(archive.glob("*.json")) if archive.is_dir() else []:
        rel = str(arch.relative_to(root))
        try:
            archived = json.loads(arch.read_text()).get("features")
        except (json.JSONDecodeError, AttributeError) as exc:
            errors.append(f"{rel}: invalid feature archive: {exc}")
            continue
        if not isinstance(archived, list):
            errors.append(f"{rel}: 'features' must be a list")
            continue
        for f in archived:
            if isinstance(f, dict) and f.get("status") != "passing":
                errors.append(f"{rel}: archived feature {f.get('id')} is not passing")
        sources.append((rel, archived))
    if not any(feats for _, feats in sources):
        errors.append("feature_list.json: no features")
        return

    by_id: dict[str, dict] = {}
    for src, i, f in ((src, i, f) for src, feats in sources for i, f in enumerate(feats)):
        where = f"{src}: features[{i}]"
        if not isinstance(f, dict):
            errors.append(f"{where}: not an object")
            continue
        for key, typ in FEATURE_KEYS.items():
            if key not in f:
                errors.append(f"{where} ({f.get('id')}): missing key '{key}'")
            elif not isinstance(f[key], typ) or (typ is int and isinstance(f[key], bool)):
                errors.append(f"{where} ({f.get('id')}): '{key}' has wrong type")
        extra = set(f) - set(FEATURE_KEYS)
        if extra:
            errors.append(f"{where} ({f.get('id')}): unknown keys {sorted(extra)}")
        fid = f.get("id")
        if isinstance(fid, str):
            if fid in by_id:
                errors.append(f"{src}: duplicate id {fid}")
            by_id[fid] = f

    owners: dict[str, str] = {}
    for fid, f in by_id.items():
        status = f.get("status")
        if status not in STATUSES:
            errors.append(f"{fid}: unknown status {status!r}")
        if not f.get("verification"):
            errors.append(f"{fid}: verification steps are required")
        for dep in f.get("depends_on") or []:
            if dep not in by_id:
                errors.append(f"{fid}: depends_on unknown feature {dep}")
            elif dep == fid:
                errors.append(f"{fid}: depends on itself")
        evidence = f.get("evidence") or []
        if len(evidence) > EVIDENCE_MAX_ITEMS:
            errors.append(f"{fid}: {len(evidence)} evidence items (max {EVIDENCE_MAX_ITEMS}); link to a PR or CI run instead")
        for item in evidence:
            if isinstance(item, str) and len(item) > EVIDENCE_MAX_CHARS:
                errors.append(
                    f"{fid}: evidence item of {len(item)} chars (max {EVIDENCE_MAX_CHARS}); "
                    "record a pointer (PR, CI run, test name), not pasted output"
                )
        if status == "passing":
            if not f.get("evidence"):
                errors.append(f"{fid}: passing requires recorded evidence")
            for dep in f.get("depends_on") or []:
                if dep in by_id and by_id[dep].get("status") != "passing":
                    errors.append(f"{fid}: passing but dependency {dep} is not")
        if status == "in_progress":
            owner = f.get("owner")
            if not owner:
                errors.append(f"{fid}: in_progress requires an owner (branch name)")
            elif owner in owners:
                errors.append(f"{fid}: owner {owner} already has {owners[owner]} in progress")
            else:
                owners[owner] = fid
        if status == "blocked" and not f.get("notes"):
            errors.append(f"{fid}: blocked requires notes explaining the blocker")
        for ref in DECISION_REF.findall(f"{f.get('human_gate') or ''} {f.get('notes') or ''}"):
            if ref not in decisions:
                errors.append(f"{fid}: references {ref}, which is not in DECISIONS.md")

    _cycles(by_id, errors)


def _cycles(by_id: dict[str, dict], errors: list[str]) -> None:
    state: dict[str, int] = {}

    def visit(fid: str, stack: list[str]) -> None:
        state[fid] = 1
        for dep in by_id[fid].get("depends_on") or []:
            if dep not in by_id:
                continue
            if state.get(dep) == 1:
                errors.append(f"dependency cycle: {' -> '.join(stack + [fid, dep])}")
            elif dep not in state:
                visit(dep, stack + [fid])
        state[fid] = 2

    for fid in by_id:
        if fid not in state:
            visit(fid, [])


def _progress(root: Path, errors: list[str]) -> None:
    path = root / "claude-progress.md"
    if not path.exists():
        return
    sessions = len(SESSION_HEADING.findall(path.read_text()))
    if sessions > PROGRESS_MAX_SESSIONS:
        errors.append(
            f"claude-progress.md: {sessions} session entries (max {PROGRESS_MAX_SESSIONS}); "
            "move the oldest to docs/progress/YYYY-MM.md"
        )


def _module_agents(root: Path, errors: list[str]) -> None:
    internal = root / "internal"
    if not internal.is_dir():
        return
    for module in sorted(p for p in internal.iterdir() if p.is_dir()):
        doc = module / "AGENTS.md"
        if not doc.exists():
            errors.append(f"{module.relative_to(root)}: missing AGENTS.md")
            continue
        lines = len(doc.read_text().splitlines())
        if lines > MODULE_AGENTS_MAX_LINES:
            errors.append(f"{doc.relative_to(root)}: {lines} lines (max {MODULE_AGENTS_MAX_LINES})")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    errors = check(root)
    for e in errors:
        print(f"harness: {e}", file=sys.stderr)
    if errors:
        print(f"harness: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print("harness: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
