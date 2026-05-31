from __future__ import annotations

import io
import urllib.error
from email.message import Message

import pytest

from lastfm_app.playlist_presets import PRESETS, parse_track_lines
from lastfm_app.spotify import SpotifyRateLimitError, _json_request, match_score, normalize


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


def test_json_request_fails_fast_on_long_spotify_rate_limit(monkeypatch) -> None:
    headers = Message()
    headers["Retry-After"] = "120"

    def raise_rate_limit(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://api.spotify.com/v1/me",
            code=429,
            msg="Too Many Requests",
            hdrs=headers,
            fp=io.BytesIO(b'{"error":"too many requests"}'),
        )

    monkeypatch.setenv("SPOTIFY_MAX_RATE_LIMIT_SLEEP_SECONDS", "1")
    monkeypatch.setattr("urllib.request.urlopen", raise_rate_limit)

    with pytest.raises(SpotifyRateLimitError) as error:
        _json_request("https://api.spotify.com/v1/me", token="token")

    assert error.value.retry_after_seconds == 120
