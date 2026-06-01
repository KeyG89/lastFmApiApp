from __future__ import annotations

from pathlib import Path

from lastfm_app.drum_grooves import parse_verified_drum_grooves, spotify_playlist_name


def test_parse_verified_drum_grooves_only_exportable_rows(tmp_path: Path) -> None:
    source = tmp_path / "grooves.md"
    source.write_text(
        """
## Drums Groove 01 - Rock 8th Notes

| Slot | Bucket | Artist | Title | Spotify Ready | BPM | BPM Source | Groove Fit | Tags / style | Last.fm plays | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | ChatGPT seed | AC/DC | Back in Black | yes | 93 | approx/common | seed/reference | rock |  | ok |
| 2 | Last.fm local | Bad Match | Remix | no | 120 | fallback | excluded | psy | 10 | no |
""",
        encoding="utf-8",
    )

    playlists = parse_verified_drum_grooves(source)

    assert len(playlists) == 1
    assert playlists[0].name == "Drums Groove 01 - Rock 8th Notes"
    assert len(playlists[0].tracks) == 1
    assert playlists[0].tracks[0].artist == "AC/DC"
    assert playlists[0].tracks[0].title == "Back in Black"


def test_spotify_playlist_name_uses_folder_like_prefix(tmp_path: Path) -> None:
    source = tmp_path / "grooves.md"
    source.write_text(
        """
## Drums Groove 22 - Hip-Hop

| Slot | Bucket | Artist | Title | Spotify Ready | BPM | BPM Source | Groove Fit | Tags / style | Last.fm plays | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | ChatGPT seed | The Roots | The Seed (2.0) | yes | 98 | approx/common | seed/reference | hip-hop |  | ok |
""",
        encoding="utf-8",
    )

    playlist = parse_verified_drum_grooves(source)[0]

    assert spotify_playlist_name(playlist) == "Drums: Grooves / 22 - Hip-Hop"
