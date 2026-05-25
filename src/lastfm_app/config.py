from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DB_PATH = Path("data/lastfm.sqlite3")


@dataclass(frozen=True)
class LastfmConfig:
    api_key: str
    shared_secret: str | None
    username: str
    app_name: str
    db_path: Path
    request_delay: float = 0.25


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def load_config(require_api: bool = True) -> LastfmConfig:
    load_dotenv()
    api_key = os.environ.get("LASTFM_API_KEY", "").strip()
    username = os.environ.get("LASTFM_USERNAME", "").strip()
    if require_api and not api_key:
        raise ValueError("LASTFM_API_KEY is required. Copy .env.example to .env and fill it in.")
    if require_api and not username:
        raise ValueError("LASTFM_USERNAME is required. Copy .env.example to .env and fill it in.")

    db_path = Path(os.environ.get("LASTFM_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
    delay_text = os.environ.get("LASTFM_REQUEST_DELAY_SECONDS", "0.25").strip()
    try:
        delay = max(0.0, float(delay_text))
    except ValueError:
        delay = 0.25

    return LastfmConfig(
        api_key=api_key,
        shared_secret=os.environ.get("LASTFM_SHARED_SECRET", "").strip() or None,
        username=username,
        app_name=os.environ.get("LASTFM_APP_NAME", "lastFmApiApp").strip() or "lastFmApiApp",
        db_path=db_path,
        request_delay=delay,
    )
