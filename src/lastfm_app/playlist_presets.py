from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlaylistTrack:
    artist: str
    track: str


@dataclass(frozen=True)
class PlaylistPreset:
    name: str
    description: str
    tracks: tuple[PlaylistTrack, ...]


PRESETS: dict[str, PlaylistPreset] = {
    "electronic-rediscover": PlaylistPreset(
        name="Rediscover: Electronic, Not Psy Trance",
        description="Energy-heavy electronic rediscovery from Last.fm scrobbles, excluding psy/goa trance.",
        tracks=(
            PlaylistTrack("Cosmic Gate", "Exploration Of Space (Hard Kandy Remix)"),
            PlaylistTrack("Underworld", "Born Slippy"),
            PlaylistTrack("Nero", "Must Be the Feeling (Delta Heavy remix)"),
            PlaylistTrack("B Complex", "Beautiful Lies"),
            PlaylistTrack("Pendulum", "Propane Nightmares"),
            PlaylistTrack("deadmau5", "Ghosts 'n' Stuff (feat. Rob Swire)"),
            PlaylistTrack("Mord Fustang", "The Electric Dream"),
            PlaylistTrack("DJ Fresh", "Louder"),
            PlaylistTrack("The Prodigy", "Omen"),
            PlaylistTrack("Justice", "Waters of Nazareth"),
        ),
    ),
    "electronic-less-obvious": PlaylistPreset(
        name="Less Obvious Electronic Morning Drive",
        description="Blog-era electro, dirty club and DnB crossover cuts from Last.fm history.",
        tracks=(
            PlaylistTrack("Far Too Loud", "Play It Loud"),
            PlaylistTrack("Cyberpunkers", "Cabala"),
            PlaylistTrack("Feed Me", "Short Skirt"),
            PlaylistTrack("Chase & Status", "Stems for Time (Sawgood Remix)"),
            PlaylistTrack("The Qemist", "Lost Weekend"),
            PlaylistTrack("Shock One", "Polygon (Dirtyphonics Remix)"),
            PlaylistTrack("Dirtyphonics", "Vandals"),
            PlaylistTrack("Freestylers", "Push Up"),
            PlaylistTrack("Digitalism", "Circles (Eric Prydz Remix)"),
            PlaylistTrack("PNAU", "Baby (Breakbot Remix)"),
        ),
    ),
    "morning-rock-bangers": PlaylistPreset(
        name="Morning Rock Bangers",
        description="Garage, hard rock and punk-leaning Last.fm rediscovery for a high-energy morning.",
        tracks=(
            PlaylistTrack("The Datsuns", "Harmonic Generator"),
            PlaylistTrack("The Hellacopters", "I'm in the Band"),
            PlaylistTrack("The Hives", "Try It Again"),
            PlaylistTrack("The Pink Spiders", "Gimme Chemicals"),
            PlaylistTrack("Cage the Elephant", "Back Against the Wall"),
            PlaylistTrack("The Raconteurs", "Consoler of the Lonely"),
            PlaylistTrack("Johnossi", "Glory Days to Come"),
            PlaylistTrack("Millencolin", "No Cigar"),
            PlaylistTrack("The Datsuns", "MF From Hell"),
            PlaylistTrack("Wolfmother", "Dimension"),
        ),
    ),
}


def parse_track_lines(text: str) -> list[PlaylistTrack]:
    tracks: list[PlaylistTrack] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if " - " not in line:
            raise ValueError(f"Playlist line must use 'Artist - Track': {line}")
        artist, track = line.split(" - ", 1)
        tracks.append(PlaylistTrack(artist.strip(), track.strip()))
    return tracks
