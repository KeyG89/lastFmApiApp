from __future__ import annotations

from lastfm_app.playlist_presets import PRESETS, parse_track_lines
from lastfm_app.spotify import match_score, normalize


def test_parse_track_lines() -> None:
    tracks = parse_track_lines(
        """
        # Morning
        The Datsuns - Get Up! (Don't Fight It)
        The Hives - Try It Again
        """
    )
    assert [(track.artist, track.track) for track in tracks] == [
        ("The Datsuns", "Get Up! (Don't Fight It)"),
        ("The Hives", "Try It Again"),
    ]


def test_spotify_match_score_prefers_exact_artist_and_track() -> None:
    wanted = PRESETS["morning-rock-bangers"].tracks[0]
    exact = {"name": "Get Up! (Don't Fight It)", "artists": [{"name": "The Datsuns"}], "popularity": 20}
    weak = {"name": "Get Up", "artists": [{"name": "Unknown"}], "popularity": 90}
    assert match_score(wanted, exact) > match_score(wanted, weak)


def test_normalize_removes_punctuation() -> None:
    assert normalize("Axwell /\\ Ingrosso") == "axwell ingrosso"
