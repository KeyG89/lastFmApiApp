from __future__ import annotations

from lastfm_app import db
from lastfm_app.shazam import (
    connect_shazam,
    ensure_shazam_schema,
    generate_shazam_playlists,
    import_shazam_api_search,
    import_spotify_shazam_playlist,
    import_shazam_file,
    link_lastfm_tracks,
    playlist_report,
    score_energy,
    shazam_status,
)


def test_import_shazam_csv_and_generate_playlists(tmp_path) -> None:
    source = tmp_path / "shazam.csv"
    source.write_text(
        "Title,Artist,Date Shazamed,Genre,Shazam URL\n"
        "Quiet Light,Low Artist,2026-05-01,ambient,https://shazam.example/quiet\n"
        "Morning Drive,Rock Artist,2026-05-02,rock,https://shazam.example/drive\n"
        "Night Circuit,Dance Artist,2026-05-03,electronic,https://shazam.example/night\n",
        encoding="utf-8",
    )
    conn = connect_shazam(tmp_path / "shazam.sqlite3")
    result = import_shazam_file(conn, source)

    assert result == {"rows_seen": 3, "rows_inserted": 3, "rows_updated": 0}
    generated = generate_shazam_playlists(conn)
    assert generated["playlists"] >= 3

    report = playlist_report(conn)
    assert "All Shazams: Calm To Energetic" in report
    assert report.index("Low Artist - Quiet Light") < report.index("Rock Artist - Morning Drive")
    assert "Shazam: Electronic" in report
    assert "Shazam: Rock" in report


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


def test_shazam_energy_score_uses_genres() -> None:
    assert score_energy("ambient", []) < score_energy("rock", [])
    assert score_energy("electronic", ["dance"]) > score_energy("folk", ["acoustic"])


def test_shazam_status_empty_database(tmp_path) -> None:
    conn = connect_shazam(tmp_path / "shazam.sqlite3")
    ensure_shazam_schema(conn)
    assert "- tracks: 0" in shazam_status(conn)


def test_import_shazam_api_search(tmp_path) -> None:
    class FakeShazamApi:
        def search(self, query: str, limit: int = 5):
            assert query == "known track"
            assert limit == 2
            return [
                {
                    "title": "Known Track",
                    "subtitle": "Known Artist",
                    "url": "https://www.shazam.com/track/123/known-track",
                    "genres": {"primary": "Electronic"},
                    "hub": {"actions": [{"uri": "https://music.apple.com/album/known-track/123"}]},
                }
            ]

    conn = connect_shazam(tmp_path / "shazam.sqlite3")
    result = import_shazam_api_search(conn, FakeShazamApi(), "known track", limit=2)

    assert result == {"rows_seen": 1, "rows_inserted": 1, "rows_updated": 0}
    row = conn.execute("SELECT artist_name, track_name, genre, shazam_url, apple_music_url FROM shazam_tracks").fetchone()
    assert dict(row) == {
        "artist_name": "Known Artist",
        "track_name": "Known Track",
        "genre": "Electronic",
        "shazam_url": "https://www.shazam.com/track/123/known-track",
        "apple_music_url": "https://music.apple.com/album/known-track/123",
    }


def test_import_spotify_shazam_playlist(tmp_path) -> None:
    class FakeSpotify:
        def playlist_tracks(self, playlist_id: str):
            assert playlist_id == "playlist1"
            return [
                {
                    "added_at": "2026-05-31T10:00:00Z",
                    "track": {
                        "id": "spotify1",
                        "uri": "spotify:track:spotify1",
                        "name": "Playlist Track",
                        "popularity": 72,
                        "external_urls": {"spotify": "https://open.spotify.com/track/spotify1"},
                        "artists": [{"name": "Playlist Artist"}],
                        "album": {"name": "Playlist Album", "album_type": "single"},
                    },
                }
            ]

    conn = connect_shazam(tmp_path / "shazam.sqlite3")
    result = import_spotify_shazam_playlist(conn, FakeSpotify(), "playlist1")

    assert result == {"rows_seen": 1, "rows_inserted": 1, "rows_updated": 0}
    row = conn.execute("SELECT spotify_track_id, spotify_uri, spotify_popularity FROM shazam_tracks").fetchone()
    assert dict(row) == {
        "spotify_track_id": "spotify1",
        "spotify_uri": "spotify:track:spotify1",
        "spotify_popularity": 72,
    }
