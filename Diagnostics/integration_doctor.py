#!/usr/bin/env python3
"""Check local integration readiness without revealing credentials."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_SPOTIFY_SCOPES = frozenset(
    "playlist-modify-private playlist-modify-public playlist-read-private "
    "playlist-read-collaborative user-library-read user-library-modify "
    "user-top-read user-read-recently-played".split()
)


@dataclass(frozen=True)
class Check:
    level: str
    name: str
    detail: str


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def setting(env_file: dict[str, str], name: str, default: str = "") -> str:
    return os.environ.get(name, env_file.get(name, default)).strip()


def tracked(root: Path, path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=root,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def local_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def spotify_redirect_is_compatible(value: str) -> bool:
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return False
    return parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and port is not None


def audit(root: Path) -> list[Check]:
    checks: list[Check] = []
    env_path = root / ".env"
    env_file = load_env(env_path)

    checks.append(
        Check(
            "pass" if sys.version_info >= (3, 11) else "fail",
            "python",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )
    checks.append(Check("pass" if env_path.exists() else "warn", "env", "present" if env_path.exists() else "copy .env.example to .env"))

    lastfm_ready = bool(setting(env_file, "LASTFM_API_KEY") and setting(env_file, "LASTFM_USERNAME"))
    checks.append(Check("pass" if lastfm_ready else "warn", "lastfm", "configured" if lastfm_ready else "LASTFM_API_KEY and/or LASTFM_USERNAME missing"))
    checks.append(
        Check(
            "pass",
            "lastfm:shared-secret",
            "configured" if setting(env_file, "LASTFM_SHARED_SECRET") else "absent (optional for current read-only methods)",
        )
    )

    spotify_client = setting(env_file, "SPOTIFY_CLIENT_ID")
    checks.append(Check("pass" if spotify_client else "warn", "spotify:client", "configured" if spotify_client else "SPOTIFY_CLIENT_ID missing"))
    redirect = setting(env_file, "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8765/callback")
    redirect_ok = spotify_redirect_is_compatible(redirect)
    checks.append(Check("pass" if redirect_ok else "fail", "spotify:redirect", "valid loopback URI" if redirect_ok else "use http://127.0.0.1:<port>/<path>"))

    token_path = local_path(root, setting(env_file, "SPOTIFY_TOKEN_PATH", "data/spotify_token.json"))
    if tracked(root, token_path):
        checks.append(Check("fail", "spotify:token", "token path is tracked by Git"))
    elif not token_path.exists():
        checks.append(Check("warn", "spotify:token", "absent; run spotify auth when Spotify access is needed"))
    else:
        try:
            token = json.loads(token_path.read_text(encoding="utf-8"))
            token_ok = bool(token.get("access_token") or token.get("refresh_token"))
            granted_scopes = set(str(token.get("scope", "")).split())
        except (OSError, json.JSONDecodeError):
            token_ok = False
            granted_scopes = set()
        missing_scopes = sorted(REQUIRED_SPOTIFY_SCOPES - granted_scopes)
        if not token_ok:
            checks.append(Check("fail", "spotify:token", "malformed token cache"))
        elif missing_scopes:
            checks.append(Check("fail", "spotify:token", f"reauthorize; missing scopes: {', '.join(missing_scopes)}"))
        else:
            checks.append(Check("pass", "spotify:token", "readable token cache with required scopes"))

    for name, variable, default in (
        ("lastfm:database", "LASTFM_DB_PATH", "data/lastfm.sqlite3"),
        ("shazam:database", "SHAZAM_DB_PATH", "data/shazam.sqlite3"),
    ):
        path = local_path(root, setting(env_file, variable, default))
        if tracked(root, path):
            checks.append(Check("fail", name, "database path is tracked by Git"))
        else:
            checks.append(Check("pass" if path.exists() else "warn", name, "present and untracked" if path.exists() else "absent; initialize when needed"))

    required_agent_files = (
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        "Docs/AgentOperations.md",
        ".agents/skills/lastfm-spotify-operator/SKILL.md",
        ".agents/skills/lastfm-spotify-operator/references/setup.md",
        ".agents/skills/lastfm-spotify-operator/references/operations.md",
        ".claude/skills/lastfm-spotify-operator/SKILL.md",
    )
    missing = [name for name in required_agent_files if not (root / name).is_file()]
    checks.append(Check("fail" if missing else "pass", "agent-onboarding", ", ".join(missing) if missing else "all entrypoints present"))
    return checks


def print_report(checks: list[Check], as_json: bool) -> int:
    if as_json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        print("Integration readiness (credential values are never displayed)")
        for check in checks:
            print(f"{check.level:4}  {check.name:24}  {check.detail}")
    return 1 if any(check.level == "fail" for check in checks) else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.path).expanduser().resolve()
    raise SystemExit(print_report(audit(root), args.json))


if __name__ == "__main__":
    main()
