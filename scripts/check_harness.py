#!/usr/bin/env python3
"""Mechanical checks for the agent harness.

A harness rule an agent can break without CI failing is a suggestion, not a
rule. This script turns the rules in AGENTS.md about feature state, decisions,
and module docs into checks. It uses only the standard library.

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
    _module_agents(root, errors)
    return errors


def _decisions(root: Path, errors: list[str]) -> set[str]:
    path = root / "DECISIONS.md"
    if not path.exists():
        return set()
    text = path.read_text()
    ids = DECISION_HEADING.findall(text)
    if len(ids) != len(set(ids)):
        errors.append("DECISIONS.md: duplicate decision IDs")
    sections = DECISION_HEADING.split(text)[1:]
    for did, body in zip(sections[::2], sections[1::2]):
        if not DECISION_STATUS.search(body):
            errors.append(f"DECISIONS.md: {did} lacks a '- **Status:** open|decided|superseded' line")
        elif DECISION_STATUS.search(body).group(1) == "open" and not DECISION_ISSUE.search(body):
            errors.append(f"DECISIONS.md: open {did} lacks a '- **Issue:** <issue URL>|pending' line")
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
    if not isinstance(features, list) or not features:
        errors.append("feature_list.json: 'features' must be a non-empty list")
        return

    by_id: dict[str, dict] = {}
    for i, f in enumerate(features):
        where = f"feature_list.json: features[{i}]"
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
                errors.append(f"feature_list.json: duplicate id {fid}")
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
