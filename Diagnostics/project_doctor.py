#!/usr/bin/env python3
"""Audit a project-builder-flow project structure."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Check:
    level: str
    name: str
    detail: str


def git_output(root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def has_secret_pattern(path: Path) -> bool:
    ignored_parts = {"__pycache__", ".venv", "venv", ".pytest_cache", "data"}
    if any(part in ignored_parts for part in path.parts):
        return False
    if "Tests" in path.parts:
        return False
    if path.name in {".env", "credentials.json", "token.json"}:
        return True
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".m4a", ".wav", ".mp3"}:
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    patterns = [
        r"hf_[A-Za-z0-9]{20,}",
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"ghp_[A-Za-z0-9]{20,}",
        r"sk-[A-Za-z0-9]{20,}",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def audit(root: Path) -> list[Check]:
    checks: list[Check] = []

    required_files = [
        "MasterPlan.md",
        "README.md",
        "AGENTS.md",
        ".env.example",
        ".gitignore",
        "Docs/Workflow.md",
        "Docs/ProjectBuilderFlow.md",
        "Docs/AutoImprovement.md",
        "Docs/TutorialUX.md",
        "Diagnostics/check.sh",
        "Diagnostics/project_doctor.py",
        "Tutorial/index.html",
        "Tutorial/assets/style.css",
        "Tests/README.md",
    ]
    required_dirs = ["Items", "Docs", "Tutorial", "Diagnostics", "Tests"]

    for directory in required_dirs:
        path = root / directory
        checks.append(Check("pass" if path.is_dir() else "fail", f"dir:{directory}", "present" if path.is_dir() else "missing"))

    for filename in required_files:
        path = root / filename
        checks.append(Check("pass" if path.is_file() else "fail", f"file:{filename}", "present" if path.is_file() else "missing"))

    if (root / ".git").is_dir():
        checks.append(Check("pass", "git", "repository initialized"))
        remote = git_output(root, ["remote", "get-url", "origin"])
        checks.append(Check("pass" if remote else "warn", "git:origin", remote or "origin remote missing"))
    else:
        checks.append(Check("fail", "git", "repository missing"))

    master = root / "MasterPlan.md"
    if master.exists():
        text = master.read_text(encoding="utf-8", errors="ignore")
        for section in ("## Project Items", "## AI Augmentations", "## Workflow Improvements"):
            checks.append(Check("pass" if section in text else "fail", f"masterplan:{section}", "present" if section in text else "missing"))

    items = list((root / "Items").glob("T.*.md")) if (root / "Items").is_dir() else []
    checks.append(Check("pass" if items else "fail", "items", f"{len(items)} item files"))
    for item in items:
        text = item.read_text(encoding="utf-8", errors="ignore")
        if "Status:" not in text:
            checks.append(Check("fail", f"item:{item.name}", "missing Status"))

    secret_hits = []
    for path in root.rglob("*"):
        if ".git" in path.parts or path.is_dir():
            continue
        if has_secret_pattern(path):
            secret_hits.append(str(path.relative_to(root)))
    checks.append(Check("fail" if secret_hits else "pass", "secrets", ", ".join(secret_hits) if secret_hits else "no obvious secrets"))

    workflow = root / ".github/workflows/ci.yml"
    checks.append(Check("pass" if workflow.exists() else "warn", "ci", "present" if workflow.exists() else "missing .github/workflows/ci.yml"))

    return checks


def print_report(checks: list[Check], as_json: bool) -> int:
    if as_json:
        print(json.dumps([check.__dict__ for check in checks], indent=2))
    else:
        widths = {
            "level": max(len("level"), *(len(check.level) for check in checks)),
            "name": max(len("check"), *(len(check.name) for check in checks)),
        }
        print(f"{'level'.ljust(widths['level'])}  {'check'.ljust(widths['name'])}  detail")
        print(f"{'-' * widths['level']}  {'-' * widths['name']}  ------")
        for check in checks:
            print(f"{check.level.ljust(widths['level'])}  {check.name.ljust(widths['name'])}  {check.detail}")
    return 1 if any(check.level == "fail" for check in checks) else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a project-builder-flow project.")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.path).expanduser().resolve()
    raise SystemExit(print_report(audit(root), args.json))


if __name__ == "__main__":
    main()
