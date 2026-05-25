from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .db import dumps


API_ROOT = "https://ws.audioscrobbler.com/2.0/"


class LastfmError(RuntimeError):
    pass


@dataclass(frozen=True)
class LastfmClient:
    api_key: str
    app_name: str = "lastFmApiApp"
    delay_seconds: float = 0.25
    timeout_seconds: float = 30.0

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        query = {
            "method": method,
            "api_key": self.api_key,
            "format": "json",
            **{key: value for key, value in params.items() if value is not None},
        }
        encoded = urllib.parse.urlencode(query)
        request = urllib.request.Request(
            f"{API_ROOT}?{encoded}",
            headers={"User-Agent": f"{self.app_name}/0.1 (+local music library importer)"},
        )
        last_error: Exception | None = None
        for attempt in range(4):
            if attempt or self.delay_seconds:
                time.sleep(self.delay_seconds * max(1, attempt + 1))
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, dict) and "error" in payload:
                    raise LastfmError(f"Last.fm API error {payload.get('error')}: {payload.get('message')}")
                return payload
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, LastfmError) as error:
                last_error = error
                if isinstance(error, LastfmError):
                    break
                time.sleep(min(8.0, 0.5 * (2**attempt)))
        raise LastfmError(str(last_error))


def params_hash(params: dict[str, Any]) -> str:
    return hashlib.sha256(dumps(params).encode("utf-8")).hexdigest()
