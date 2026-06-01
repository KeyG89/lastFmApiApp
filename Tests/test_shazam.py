from __future__ import annotations

from lastfm_app import db
from lastfm_app.shazam import (
    connect_shazam,
    enrich_from_lastfm,
    ensure_shazam_schema,
    export_shazam_playlists_to_spotify,
    generate_shazam_playlists,
    import_shazam_file,
    link_lastfm_tracks,
    playlist_report,
    score_energy,
    shazam_status,
    spotify_export_report,
)


def test_import_shazam_csv_and_generate_playlists(tmp_path) -> None:
    source = tmp_path / "shazam.csv"
    source.write_text(
        "Title,Artist,Date Shazamed,Genre,Shazam URL\n"
        "Quiet Light,Low Artist,2026-05-01,ambient,https://shazam.example/quiet\n"
        "Morning Drive,Rock Artist,2026-05-02,rock,https://shazam.example/drive\n"
        "Night Circuit,Dance Artist,2026-05-03,electronic,https://shazam.example/night\n"
        "Unknown State,Various Artist,2026-05-04,,https://shazam.example/unknown\n",
        encoding="utf-8",
    )
    conn = connect_shazam(tmp_path / "shazam.sqlite3")
    result = import_shazam_file(conn, source)

    assert result == {"rows_seen": 4, "rows_inserted": 4, "rows_updated": 0}
    generated = generate_shazam_playlists(conn)
    assert generated["playlists"] >= 3

    report = playlist_report(conn)
    assert "Shazam: Energy High To Low" in report
    assert report.index("Rock Artist - Morning Drive") < report.index("Low Artist - Quiet Light")
    assert "Shazam: Electronic" in report
    assert "Shazam: Rock" in report
    assert "Shazam: Various" in report


def test_import_web_shazam_csv_with_preamble_and_track_key(tmp_path) -> None:
    source = tmp_path / "shazamlibrary.csv"
    source.write_text(
        "Shazam Library\n"
        "Index,TagTime,Title,Artist,URL,TrackKey\n"
        '1,2026-04-18,"My Lovely Man","Red Hot Chili Peppers",https://www.shazam.com/track/226699/my-lovely-man,226699\n',
        encoding="utf-8",
    )
    conn = connect_shazam(tmp_path / "shazam.sqlite3")
    result = import_shazam_file(conn, source)

    assert result == {"rows_seen": 1, "rows_inserted": 1, "rows_updated": 0}
    row = conn.execute(
        """
        SELECT unique_key, source_index, shazam_track_key, artist_name, track_name, shazamed_at, shazam_url
        FROM shazam_tracks
        """
    ).fetchone()
    assert dict(row) == {
        "unique_key": "shazam:226699",
        "source_index": 1,
        "shazam_track_key": "226699",
        "artist_name": "Red Hot Chili Peppers",
        "track_name": "My Lovely Man",
        "shazamed_at": "2026-04-18",
        "shazam_url": "https://www.shazam.com/track/226699/my-lovely-man",
    }


def test_shazam_import_links_to_lastfm(tmp_path) -> None:
    lastfm_conn = db.connect(tmp_path / "lastfm.sqlite3")
    db.init_db(lastfm_conn)
    artist_id = db.upsert_artist(lastfm_conn, "Known Artist")
    track_id = db.upsert_track(lastfm_conn, artist_id, None, "Known Track")
    lastfm_conn.commit()

    source = tmp_path / "shazam.csv"
    source.write_text("Title,Artist\nKnown Track,Known Artist\n", encoding="utf-8")
    shazam_conn = connect_shazam(tmp_path / "shazam.sqlite3")
    import_shazam_file(shazam_conn, source)

    assert link_lastfm_tracks(shazam_conn, lastfm_conn) == 1
    row = shazam_conn.execute("SELECT lastfm_track_id FROM shazam_tracks").fetchone()
    assert row["lastfm_track_id"] == track_id


def test_shazam_enriches_tags_from_lastfm(tmp_path) -> None:
    lastfm_conn = db.connect(tmp_path / "lastfm.sqlite3")
    db.init_db(lastfm_conn)
    artist_id = db.upsert_artist(lastfm_conn, "Known Artist")
    track_id = db.upsert_track(lastfm_conn, artist_id, None, "Known Track")
    for tag_id, weight in db.upsert_tags(lastfm_conn, [("electronic", 100), ("rock", 60)]):
        lastfm_conn.execute(
            "INSERT INTO track_tags(track_id, tag_id, weight, source) VALUES(?, ?, ?, 'test')",
            (track_id, tag_id, weight),
        )
    lastfm_conn.commit()

    source = tmp_path / "shazam.csv"
    source.write_text("Title,Artist\nKnown Track,Known Artist\n", encoding="utf-8")
    shazam_conn = connect_shazam(tmp_path / "shazam.sqlite3")
    import_shazam_file(shazam_conn, source)
    link_lastfm_tracks(shazam_conn, lastfm_conn)

    assert enrich_from_lastfm(shazam_conn, lastfm_conn) == 1
    row = shazam_conn.execute("SELECT genre, tags_json, energy_score FROM shazam_tracks").fetchone()
    assert row["genre"] == "electronic"
    assert "electronic" in row["tags_json"]
    assert row["energy_score"] > 50


def test_shazam_energy_score_uses_genres() -> None:
    assert score_energy("ambient", []) < score_energy("rock", [])
    assert score_energy("electronic", ["dance"]) > score_energy("folk", ["acoustic"])


def test_shazam_status_empty_database(tmp_path) -> None:
    conn = connect_shazam(tmp_path / "shazam.sqlite3")
    ensure_shazam_schema(conn)
    assert "- tracks: 0" in shazam_status(conn)


def test_export_shazam_playlists_to_spotify_records_mapping(tmp_path, monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("lastfm_app.shazam.time.sleep", lambda seconds: sleeps.append(seconds))

    class FakeSpotify:
        def __init__(self) -> None:
            self.created: list[dict] = []

        def search_track(self, track):
            return {
                "id": f"id-{track.artist}-{track.track}",
                "uri": f"spotify:track:{track.artist}:{track.track}",
                "external_urls": {"spotify": f"https://open.spotify.test/{track.artist}/{track.track}"},
                "popularity": 50,
            }

        def create_playlist(self, name: str, description: str, public: bool = False):
            playlist = {
                "id": f"playlist-{len(self.created) + 1}",
                "uri": f"spotify:playlist:{len(self.created) + 1}",
                "external_urls": {"spotify": f"https://open.spotify.test/playlist/{len(self.created) + 1}"},
                "name": name,
            }
            self.created.append(playlist)
            return playlist

        def add_items(self, playlist_id: str, uris: list[str]) -> None:
            assert playlist_id
            assert uris

    source = tmp_path / "shazam.csv"
    source.write_text(
        "Title,Artist,Genre\n"
        "Quiet Light,Low Artist,ambient\n"
        "Morning Drive,Rock Artist,rock\n",
        encoding="utf-8",
    )
    conn = connect_shazam(tmp_path / "shazam.sqlite3")
    import_shazam_file(conn, source)
    generate_shazam_playlists(conn)

    result = export_shazam_playlists_to_spotify(conn, FakeSpotify(), request_delay_seconds=10)

    assert result["exported"] >= 2
    assert result["tracks_added"] >= 4
    assert sleeps
    assert set(sleeps) == {10}
    assert "Shazam Spotify Exports" in spotify_export_report(conn)
    row = conn.execute("SELECT spotify_playlist_id, tracks_added FROM shazam_spotify_playlist_exports ORDER BY id LIMIT 1").fetchone()
    assert row["spotify_playlist_id"].startswith("playlist-")
    assert row["tracks_added"] > 0
