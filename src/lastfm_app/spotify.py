from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import load_dotenv
from .playlist_presets import PlaylistTrack


AUTH_ROOT = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_ROOT = "https://api.spotify.com/v1"
SCOPES = "playlist-modify-private playlist-modify-public"


class SpotifyError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpotifyConfig:
    client_id: str
    redirect_uri: str
    token_path: Path
    market: str | None = None


def load_spotify_config(require_client: bool = True) -> SpotifyConfig:
    import os

    load_dotenv()
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    if require_client and not client_id:
        raise ValueError("SPOTIFY_CLIENT_ID is required in .env")
    return SpotifyConfig(
        client_id=client_id,
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8765/callback").strip(),
        token_path=Path(os.environ.get("SPOTIFY_TOKEN_PATH", "data/spotify_token.json")).expanduser(),
        market=os.environ.get("SPOTIFY_MARKET", "PL").strip() or None,
    )


def _code_verifier() -> str:
    return secrets.token_urlsafe(64)[:128]


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _json_request(url: str, method: str = "GET", token: str | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        raise SpotifyError(f"Spotify HTTP {error.code}: {raw[:500]}") from error


def _form_request(url: str, data: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        raise SpotifyError(f"Spotify auth HTTP {error.code}: {raw[:500]}") from error


def authenticate(config: SpotifyConfig, open_browser: bool = True) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(config.redirect_uri)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise SpotifyError("SPOTIFY_REDIRECT_URI must point to localhost for CLI auth.")
    if not parsed.port:
        raise SpotifyError("SPOTIFY_REDIRECT_URI must include a port, for example http://127.0.0.1:8765/callback")

    verifier = _code_verifier()
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": config.redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": _code_challenge(verifier),
    }
    auth_url = f"{AUTH_ROOT}?{urllib.parse.urlencode(params)}"
    result: dict[str, str] = {}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result["code"] = query.get("code", [""])[0]
            result["state"] = query.get("state", [""])[0]
            result["error"] = query.get("error", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Spotify authorization complete.</h1><p>You can close this tab.</p></body></html>")

    print(f"Open this Spotify authorization URL:\n{auth_url}")
    if open_browser:
        webbrowser.open(auth_url)
    server = http.server.HTTPServer((parsed.hostname or "127.0.0.1", parsed.port), CallbackHandler)
    server.handle_request()

    if result.get("error"):
        raise SpotifyError(f"Spotify authorization failed: {result['error']}")
    if result.get("state") != state or not result.get("code"):
        raise SpotifyError("Spotify authorization failed: invalid callback state or missing code.")

    token = _form_request(
        TOKEN_URL,
        {
            "client_id": config.client_id,
            "grant_type": "authorization_code",
            "code": result["code"],
            "redirect_uri": config.redirect_uri,
            "code_verifier": verifier,
        },
    )
    token["created_at"] = int(time.time())
    config.token_path.parent.mkdir(parents=True, exist_ok=True)
    config.token_path.write_text(json.dumps(token, indent=2), encoding="utf-8")
    return token


def load_token(config: SpotifyConfig) -> dict[str, Any]:
    if not config.token_path.exists():
        raise SpotifyError("Spotify token missing. Run: lastfm-app spotify auth")
    token = json.loads(config.token_path.read_text(encoding="utf-8"))
    created_at = int(token.get("created_at", 0))
    expires_in = int(token.get("expires_in", 0))
    if token.get("refresh_token") and created_at + expires_in - 60 <= int(time.time()):
        refreshed = _form_request(
            TOKEN_URL,
            {
                "client_id": config.client_id,
                "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"],
            },
        )
        token.update(refreshed)
        token["refresh_token"] = token.get("refresh_token") or refreshed.get("refresh_token") or token["refresh_token"]
        token["created_at"] = int(time.time())
        config.token_path.write_text(json.dumps(token, indent=2), encoding="utf-8")
    return token


def normalize(value: str) -> str:
    keep = []
    for char in value.casefold():
        keep.append(char if char.isalnum() else " ")
    return " ".join("".join(keep).split())


def match_score(wanted: PlaylistTrack, item: dict[str, Any]) -> int:
    wanted_track = normalize(wanted.track)
    wanted_artist = normalize(wanted.artist)
    item_track = normalize(item.get("name", ""))
    item_artists = " ".join(normalize(artist.get("name", "")) for artist in item.get("artists", []))
    score = 0
    if wanted_track == item_track:
        score += 70
    elif wanted_track in item_track or item_track in wanted_track:
        score += 45
    if wanted_artist and wanted_artist in item_artists:
        score += 30
    score += min(10, int(item.get("popularity") or 0) // 10)
    return score


class SpotifyClient:
    def __init__(self, config: SpotifyConfig):
        self.config = config
        self.token = load_token(config)

    @property
    def access_token(self) -> str:
        return str(self.token["access_token"])

    def me(self) -> dict[str, Any]:
        return _json_request(f"{API_ROOT}/me", token=self.access_token)

    def search_track(self, track: PlaylistTrack) -> dict[str, Any] | None:
        query = f'track:"{track.track}" artist:"{track.artist}"'
        params = {"q": query, "type": "track", "limit": "10"}
        if self.config.market:
            params["market"] = self.config.market
        url = f"{API_ROOT}/search?{urllib.parse.urlencode(params)}"
        payload = _json_request(url, token=self.access_token)
        items = payload.get("tracks", {}).get("items", [])
        if not items:
            fallback = {"q": f"{track.artist} {track.track}", "type": "track", "limit": "10"}
            if self.config.market:
                fallback["market"] = self.config.market
            payload = _json_request(f"{API_ROOT}/search?{urllib.parse.urlencode(fallback)}", token=self.access_token)
            items = payload.get("tracks", {}).get("items", [])
        if not items:
            return None
        return max(items, key=lambda item: match_score(track, item))

    def create_playlist(self, name: str, description: str, public: bool = False) -> dict[str, Any]:
        return _json_request(
            f"{API_ROOT}/me/playlists",
            method="POST",
            token=self.access_token,
            data={"name": name, "description": description, "public": public},
        )

    def add_items(self, playlist_id: str, uris: list[str]) -> None:
        for index in range(0, len(uris), 100):
            _json_request(
                f"{API_ROOT}/playlists/{playlist_id}/items",
                method="POST",
                token=self.access_token,
                data={"uris": uris[index : index + 100]},
            )


def save_spotify_matches(conn: sqlite3.Connection, matches: list[tuple[PlaylistTrack, dict[str, Any] | None]]) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS spotify_track_matches (
          artist_name TEXT NOT NULL,
          track_name TEXT NOT NULL,
          spotify_uri TEXT,
          spotify_track_name TEXT,
          spotify_artist_names TEXT,
          match_json TEXT,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(artist_name, track_name)
        )
        """
    )
    for wanted, match in matches:
        if match:
            conn.execute(
                """
                INSERT OR REPLACE INTO spotify_track_matches(
                  artist_name, track_name, spotify_uri, spotify_track_name, spotify_artist_names, match_json, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    wanted.artist,
                    wanted.track,
                    match.get("uri"),
                    match.get("name"),
                    ", ".join(artist.get("name", "") for artist in match.get("artists", [])),
                    json.dumps(match, ensure_ascii=False, sort_keys=True),
                ),
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO spotify_track_matches(
                  artist_name, track_name, spotify_uri, spotify_track_name, spotify_artist_names, match_json, updated_at
                ) VALUES(?, ?, NULL, NULL, NULL, NULL, CURRENT_TIMESTAMP)
                """,
                (wanted.artist, wanted.track),
            )
    conn.commit()
