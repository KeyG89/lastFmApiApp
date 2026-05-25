from __future__ import annotations

from lastfm_app import db
from lastfm_app.importer import import_track_scrobble, parse_scrobble_time, tag_pairs


def test_parse_scrobble_time_skips_now_playing() -> None:
    assert parse_scrobble_time({"@attr": {"nowplaying": "true"}}) is None


def test_import_scrobble_deduplicates(tmp_path) -> None:
    conn = db.connect(tmp_path / "library.sqlite3")
    db.init_db(conn)
    track = {
        "artist": {"#text": "Failure", "mbid": ""},
        "name": "Another Space Song",
        "album": {"#text": "Fantastic Planet"},
        "date": {"uts": "1700000000"},
        "url": "https://www.last.fm/music/Failure/_/Another+Space+Song",
    }
    assert import_track_scrobble(conn, track) is True
    assert import_track_scrobble(conn, track) is False
    db.recompute_stats(conn)

    assert conn.execute("SELECT COUNT(*) AS count FROM artists").fetchone()["count"] == 1
    assert conn.execute("SELECT COUNT(*) AS count FROM tracks").fetchone()["count"] == 1
    assert conn.execute("SELECT COUNT(*) AS count FROM scrobbles").fetchone()["count"] == 1
    assert conn.execute("SELECT playcount FROM user_track_stats").fetchone()["playcount"] == 1


def test_tag_pairs_accepts_single_and_list_payloads() -> None:
    assert tag_pairs({"toptags": {"tag": {"name": "shoegaze", "count": "100"}}}) == [("shoegaze", 100)]
    assert tag_pairs({"toptags": {"tag": [{"name": "rock", "count": "50"}]}}) == [("rock", 50)]
