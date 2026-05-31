from __future__ import annotations

import pytest

from lastfm_app import db
from lastfm_app.spotify import (
    SpotifyError,
    ensure_spotify_schema,
    playlist_is_protected,
    protected_confirmation_phrase,
    require_playlist_confirmation,
    upsert_spotify_playlist,
)


def test_unknown_spotify_playlist_is_protected(tmp_path) -> None:
    conn = db.connect(tmp_path / "library.sqlite3")
    db.init_db(conn)
    protected, reason = playlist_is_protected(conn, "missing")
    assert protected is True
    assert "unknown" in reason


def test_synced_external_playlist_requires_confirmation(tmp_path) -> None:
    conn = db.connect(tmp_path / "library.sqlite3")
    db.init_db(conn)
    ensure_spotify_schema(conn)
    conn.execute("INSERT INTO spotify_accounts(id, display_name) VALUES('me', 'Me')")
    playlist = {"id": "old1", "name": "Old Playlist", "owner": {"id": "me"}, "tracks": {"total": 10}}
    upsert_spotify_playlist(conn, "me", playlist, created_by_app=False)

    with pytest.raises(SpotifyError):
        require_playlist_confirmation(conn, "rename", "old1", None)

    phrase = protected_confirmation_phrase("rename", "old1", "Old Playlist")
    require_playlist_confirmation(conn, "rename", "old1", phrase)


def test_app_created_playlist_after_cutoff_is_editable(tmp_path) -> None:
    conn = db.connect(tmp_path / "library.sqlite3")
    db.init_db(conn)
    ensure_spotify_schema(conn)
    conn.execute("INSERT INTO spotify_accounts(id, display_name) VALUES('me', 'Me')")
    playlist = {"id": "new1", "name": "New Playlist", "owner": {"id": "me"}, "tracks": {"total": 10}}
    upsert_spotify_playlist(conn, "me", playlist, created_by_app=True)

    protected, _ = playlist_is_protected(conn, "new1")
    assert protected is False
    require_playlist_confirmation(conn, "rename", "new1", None)
