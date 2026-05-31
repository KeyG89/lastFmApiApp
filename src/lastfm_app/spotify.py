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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import load_dotenv
from .playlist_presets import PlaylistTrack


AUTH_ROOT = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_ROOT = "https://api.spotify.com/v1"
SCOPES = (
    "playlist-modify-private playlist-modify-public playlist-read-private "
    "playlist-read-collaborative user-library-read user-library-modify "
    "user-top-read user-read-recently-played"
)
SPOTIFY_PROTECTION_CUTOFF = "2026-05-31"


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
    for attempt in range(4):
        request = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            if error.code == 429 and attempt < 3:
                retry_after = error.headers.get("Retry-After", "5")
                try:
                    delay = max(1, int(retry_after))
                except ValueError:
                    delay = 5
                time.sleep(delay)
                continue
            raise SpotifyError(f"Spotify HTTP {error.code}: {raw[:500]}") from error
    raise SpotifyError("Spotify request failed after retries")


def _paged_get(url: str, token: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    while url:
        payload = _json_request(url, token=token)
        items.extend(payload.get("items", []))
        url = payload.get("next") or ""
    return items


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

    def list_playlists(self) -> list[dict[str, Any]]:
        return _paged_get(f"{API_ROOT}/me/playlists?limit=50", self.access_token)

    def playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        fields = "items(added_at,track(id,uri,name,duration_ms,explicit,popularity,external_urls,artists(id,uri,name),album(id,uri,name,release_date,album_type,artists(id,uri,name)))),next"
        params = {"limit": "50", "fields": fields, "additional_types": "track"}
        if self.config.market:
            params["market"] = self.config.market
        url = f"{API_ROOT}/playlists/{playlist_id}/items?{urllib.parse.urlencode(params)}"
        return _paged_get(url, self.access_token)

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
        best = max(items, key=lambda item: match_score(track, item))
        if match_score(track, best) < 60:
            return None
        return best

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

    def update_playlist_details(self, playlist_id: str, name: str | None = None, description: str | None = None, public: bool | None = None) -> None:
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if public is not None:
            data["public"] = public
        if data:
            _json_request(f"{API_ROOT}/playlists/{playlist_id}", method="PUT", token=self.access_token, data=data)

    def replace_playlist_items(self, playlist_id: str, uris: list[str]) -> None:
        _json_request(f"{API_ROOT}/playlists/{playlist_id}/tracks", method="PUT", token=self.access_token, data={"uris": uris[:100]})
        if len(uris) > 100:
            self.add_items(playlist_id, uris[100:])

    def remove_playlist_items(self, playlist_id: str, uris: list[str]) -> None:
        for index in range(0, len(uris), 100):
            _json_request(
                f"{API_ROOT}/playlists/{playlist_id}/tracks",
                method="DELETE",
                token=self.access_token,
                data={"tracks": [{"uri": uri} for uri in uris[index : index + 100]]},
            )

    def unfollow_playlist(self, playlist_id: str) -> None:
        _json_request(f"{API_ROOT}/playlists/{playlist_id}/followers", method="DELETE", token=self.access_token)


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


def ensure_spotify_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS spotify_accounts (
          id TEXT PRIMARY KEY,
          display_name TEXT,
          uri TEXT,
          external_url TEXT,
          country TEXT,
          product TEXT,
          raw_json TEXT,
          synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS spotify_playlists (
          id TEXT PRIMARY KEY,
          account_id TEXT REFERENCES spotify_accounts(id),
          name TEXT NOT NULL,
          description TEXT,
          owner_id TEXT,
          owner_name TEXT,
          public INTEGER,
          collaborative INTEGER,
          snapshot_id TEXT,
          uri TEXT,
          external_url TEXT,
          total_tracks INTEGER,
          created_by_app INTEGER NOT NULL DEFAULT 0,
          created_at_known INTEGER NOT NULL DEFAULT 0,
          created_at TEXT,
          protected INTEGER NOT NULL DEFAULT 1,
          first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          raw_json TEXT
        );

        CREATE TABLE IF NOT EXISTS spotify_artists (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          normalized_name TEXT NOT NULL,
          uri TEXT,
          raw_json TEXT,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS spotify_albums (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          normalized_name TEXT NOT NULL,
          uri TEXT,
          album_type TEXT,
          release_date TEXT,
          primary_artist_id TEXT REFERENCES spotify_artists(id),
          raw_json TEXT,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS spotify_tracks (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          normalized_name TEXT NOT NULL,
          uri TEXT NOT NULL UNIQUE,
          album_id TEXT REFERENCES spotify_albums(id),
          primary_artist_id TEXT REFERENCES spotify_artists(id),
          duration_ms INTEGER,
          explicit INTEGER,
          popularity INTEGER,
          external_url TEXT,
          raw_json TEXT,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS spotify_playlist_tracks (
          playlist_id TEXT NOT NULL REFERENCES spotify_playlists(id) ON DELETE CASCADE,
          track_id TEXT NOT NULL REFERENCES spotify_tracks(id) ON DELETE CASCADE,
          position INTEGER NOT NULL,
          added_at TEXT,
          synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(playlist_id, track_id, position)
        );

        CREATE TABLE IF NOT EXISTS spotify_lastfm_track_links (
          spotify_track_id TEXT NOT NULL REFERENCES spotify_tracks(id) ON DELETE CASCADE,
          lastfm_track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
          match_type TEXT NOT NULL,
          score INTEGER NOT NULL,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(spotify_track_id, lastfm_track_id)
        );

        CREATE TABLE IF NOT EXISTS spotify_operation_backlog (
          id INTEGER PRIMARY KEY,
          operation TEXT NOT NULL,
          target_type TEXT NOT NULL,
          target_id TEXT,
          target_name TEXT,
          status TEXT NOT NULL,
          protected_target INTEGER NOT NULL DEFAULT 0,
          confirmation TEXT,
          details_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_spotify_tracks_norm ON spotify_tracks(normalized_name, primary_artist_id);
        CREATE INDEX IF NOT EXISTS idx_spotify_artists_norm ON spotify_artists(normalized_name);
        CREATE INDEX IF NOT EXISTS idx_spotify_playlist_tracks_playlist ON spotify_playlist_tracks(playlist_id, position);
        """
    )
    conn.commit()


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log_operation(
    conn: sqlite3.Connection,
    operation: str,
    target_type: str,
    status: str,
    target_id: str | None = None,
    target_name: str | None = None,
    protected_target: bool = False,
    confirmation: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    ensure_spotify_schema(conn)
    conn.execute(
        """
        INSERT INTO spotify_operation_backlog(
          operation, target_type, target_id, target_name, status, protected_target, confirmation, details_json
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            operation,
            target_type,
            target_id,
            target_name,
            status,
            1 if protected_target else 0,
            confirmation,
            json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
        ),
    )
    conn.commit()


def protected_confirmation_phrase(operation: str, playlist_id: str, playlist_name: str) -> str:
    return f"CONFIRM {operation.upper()} OLD PLAYLIST {playlist_id} {playlist_name}"


def playlist_is_protected(conn: sqlite3.Connection, playlist_id: str) -> tuple[bool, str]:
    ensure_spotify_schema(conn)
    row = conn.execute(
        "SELECT name, protected, created_at, created_at_known FROM spotify_playlists WHERE id = ?",
        (playlist_id,),
    ).fetchone()
    if row is None:
        return True, "unknown playlist; treating as protected"
    if int(row["protected"]):
        return True, "playlist is old or creation date is unknown"
    return False, "playlist was created by this app after the protection cutoff"


def require_playlist_confirmation(conn: sqlite3.Connection, operation: str, playlist_id: str, confirmation: str | None) -> None:
    protected, reason = playlist_is_protected(conn, playlist_id)
    if not protected:
        return
    row = conn.execute("SELECT name FROM spotify_playlists WHERE id = ?", (playlist_id,)).fetchone()
    name = row["name"] if row else "UNKNOWN"
    phrase = protected_confirmation_phrase(operation, playlist_id, name)
    if confirmation != phrase:
        log_operation(
            conn,
            operation,
            "playlist",
            "blocked_confirmation_required",
            target_id=playlist_id,
            target_name=name,
            protected_target=True,
            confirmation=confirmation,
            details={"reason": reason, "required_confirmation": phrase},
        )
        raise SpotifyError(f"Protected playlist. Re-run with: --confirm {phrase!r}")


def sync_spotify_library(conn: sqlite3.Connection, client: SpotifyClient) -> dict[str, int]:
    ensure_spotify_schema(conn)
    account = client.me()
    account_id = account["id"]
    conn.execute(
        """
        INSERT OR REPLACE INTO spotify_accounts(id, display_name, uri, external_url, country, product, raw_json, synced_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account_id,
            account.get("display_name"),
            account.get("uri"),
            account.get("external_urls", {}).get("spotify"),
            account.get("country"),
            account.get("product"),
            json.dumps(account, ensure_ascii=False, sort_keys=True),
        ),
    )
    playlist_count = 0
    track_count = 0
    for playlist in client.list_playlists():
        playlist_count += 1
        upsert_spotify_playlist(conn, account_id, playlist, created_by_app=False)
        owner_id = playlist.get("owner", {}).get("id")
        if owner_id != account_id:
            log_operation(
                conn,
                "sync_playlist_tracks",
                "playlist",
                "skipped_not_owner",
                target_id=playlist["id"],
                target_name=playlist.get("name"),
                protected_target=True,
                details={"owner_id": owner_id},
            )
            continue
        conn.execute("DELETE FROM spotify_playlist_tracks WHERE playlist_id = ?", (playlist["id"],))
        try:
            playlist_items = client.playlist_tracks(playlist["id"])
        except SpotifyError as error:
            log_operation(
                conn,
                "sync_playlist_tracks",
                "playlist",
                "skipped",
                target_id=playlist["id"],
                target_name=playlist.get("name"),
                protected_target=True,
                details={"error": str(error)},
            )
            continue
        for position, item in enumerate(playlist_items):
            track = item.get("track")
            if not track or not track.get("id"):
                continue
            upsert_spotify_track(conn, track)
            conn.execute(
                """
                INSERT OR REPLACE INTO spotify_playlist_tracks(playlist_id, track_id, position, added_at, synced_at)
                VALUES(?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (playlist["id"], track["id"], position, item.get("added_at")),
            )
            link_spotify_track_to_lastfm(conn, track)
            track_count += 1
        conn.commit()
    log_operation(conn, "sync_library", "spotify_account", "done", target_id=account_id, details={"playlists": playlist_count, "playlist_tracks": track_count})
    return {"playlists": playlist_count, "playlist_tracks": track_count}


def upsert_spotify_playlist(conn: sqlite3.Connection, account_id: str | None, playlist: dict[str, Any], created_by_app: bool) -> None:
    created_at = now_utc() if created_by_app else None
    protected = 0 if created_by_app and (created_at[:10] >= SPOTIFY_PROTECTION_CUTOFF) else 1
    existing = conn.execute("SELECT created_by_app, created_at, protected FROM spotify_playlists WHERE id = ?", (playlist["id"],)).fetchone()
    if existing and int(existing["created_by_app"]):
        created_by_app = True
        created_at = existing["created_at"]
        protected = int(existing["protected"])
    conn.execute(
        """
        INSERT INTO spotify_playlists(
          id, account_id, name, description, owner_id, owner_name, public, collaborative, snapshot_id, uri,
          external_url, total_tracks, created_by_app, created_at_known, created_at, protected, raw_json, last_seen_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
          account_id=COALESCE(excluded.account_id, spotify_playlists.account_id),
          name=excluded.name,
          description=excluded.description,
          owner_id=excluded.owner_id,
          owner_name=excluded.owner_name,
          public=excluded.public,
          collaborative=excluded.collaborative,
          snapshot_id=excluded.snapshot_id,
          uri=excluded.uri,
          external_url=excluded.external_url,
          total_tracks=excluded.total_tracks,
          created_by_app=MAX(spotify_playlists.created_by_app, excluded.created_by_app),
          created_at_known=MAX(spotify_playlists.created_at_known, excluded.created_at_known),
          created_at=COALESCE(spotify_playlists.created_at, excluded.created_at),
          protected=MIN(spotify_playlists.protected, excluded.protected),
          raw_json=excluded.raw_json,
          last_seen_at=CURRENT_TIMESTAMP
        """,
        (
            playlist["id"],
            account_id,
            playlist.get("name", ""),
            playlist.get("description"),
            playlist.get("owner", {}).get("id"),
            playlist.get("owner", {}).get("display_name"),
            1 if playlist.get("public") else 0,
            1 if playlist.get("collaborative") else 0,
            playlist.get("snapshot_id"),
            playlist.get("uri"),
            playlist.get("external_urls", {}).get("spotify"),
            playlist.get("tracks", {}).get("total"),
            1 if created_by_app else 0,
            1 if created_by_app else 0,
            created_at,
            protected,
            json.dumps(playlist, ensure_ascii=False, sort_keys=True),
        ),
    )
    conn.commit()


def upsert_spotify_track(conn: sqlite3.Connection, track: dict[str, Any]) -> None:
    album = track.get("album") or {}
    artists = track.get("artists") or []
    primary_artist = artists[0] if artists else {}
    album_artists = album.get("artists") or []
    primary_album_artist = album_artists[0] if album_artists else primary_artist
    for artist in [*artists, *album_artists]:
        if artist.get("id"):
            upsert_spotify_artist(conn, artist)
    if album.get("id"):
        conn.execute(
            """
            INSERT OR REPLACE INTO spotify_albums(
              id, name, normalized_name, uri, album_type, release_date, primary_artist_id, raw_json, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                album["id"],
                album.get("name", ""),
                normalize(album.get("name", "")),
                album.get("uri"),
                album.get("album_type"),
                album.get("release_date"),
                primary_album_artist.get("id"),
                json.dumps(album, ensure_ascii=False, sort_keys=True),
            ),
        )
    conn.execute(
        """
        INSERT OR REPLACE INTO spotify_tracks(
          id, name, normalized_name, uri, album_id, primary_artist_id, duration_ms, explicit, popularity, external_url, raw_json, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            track["id"],
            track.get("name", ""),
            normalize(track.get("name", "")),
            track.get("uri"),
            album.get("id"),
            primary_artist.get("id"),
            track.get("duration_ms"),
            1 if track.get("explicit") else 0,
            track.get("popularity"),
            track.get("external_urls", {}).get("spotify"),
            json.dumps(track, ensure_ascii=False, sort_keys=True),
        ),
    )


def upsert_spotify_artist(conn: sqlite3.Connection, artist: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO spotify_artists(id, name, normalized_name, uri, raw_json, updated_at)
        VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            artist["id"],
            artist.get("name", ""),
            normalize(artist.get("name", "")),
            artist.get("uri"),
            json.dumps(artist, ensure_ascii=False, sort_keys=True),
        ),
    )


def link_spotify_track_to_lastfm(conn: sqlite3.Connection, spotify_track: dict[str, Any]) -> None:
    artists = spotify_track.get("artists") or []
    if not artists:
        return
    artist_norm = normalize(artists[0].get("name", ""))
    track_norm = normalize(spotify_track.get("name", ""))
    row = conn.execute(
        """
        SELECT t.id
        FROM tracks t
        JOIN artists a ON a.id = t.artist_id
        WHERE t.normalized_name = ? AND a.normalized_name = ?
        """,
        (track_norm, artist_norm),
    ).fetchone()
    if not row:
        return
    conn.execute(
        """
        INSERT OR REPLACE INTO spotify_lastfm_track_links(spotify_track_id, lastfm_track_id, match_type, score, updated_at)
        VALUES(?, ?, 'normalized_artist_track', 100, CURRENT_TIMESTAMP)
        """,
        (spotify_track["id"], row["id"]),
    )
