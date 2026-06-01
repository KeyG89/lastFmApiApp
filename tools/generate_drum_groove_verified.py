from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Docs" / "DrumGrooveStudyPlaylists.md"
TARGET = ROOT / "Docs" / "DrumGrooveStudyPlaylistsVerified.md"


@dataclass(frozen=True)
class Row:
    section: str
    slot: str
    bucket: str
    artist: str
    title: str
    tags: str
    plays: str


SECTION_DEFAULT_BPM = {
    "Rock 8th Notes": "110",
    "Shuffle": "120",
    "Funk": "105",
    "Disco / Four On The Floor": "120",
    "Swing": "150",
    "Bossa Nova": "130",
    "Samba": "105",
    "Reggae One Drop": "76",
    "Afrobeat": "115",
    "Odd Meters 5/4, 7/8": "100",
    "Motown": "120",
    "New Orleans Groove": "100",
    "Cha-Cha": "120",
    "Mambo": "120",
    "Songo": "105",
    "Rumba": "95",
    "Country Train Beat": "110",
    "Country Shuffle": "125",
    "Ska": "150",
    "Dub": "72",
    "House": "124",
    "Hip-Hop": "92",
    "Jazz Waltz 3/4": "130",
    "Afro-Cuban 6/8": "120",
}


BPM = {
    ("AC/DC", "Highway to Hell"): "115",
    ("AC/DC", "Back in Black"): "93",
    ("Nirvana", "Smells Like Teen Spirit"): "117",
    ("The Cranberries", "Zombie"): "83",
    ("Green Day", "Boulevard of Broken Dreams"): "84",
    ("AC/DC", "You Shook Me All Night Long"): "127",
    ("Queen", "We Will Rock You"): "81",
    ("The White Stripes", "Seven Nation Army"): "124",
    ("Joan Jett & The Blackhearts", "I Love Rock N Roll"): "94",
    ("The Rolling Stones", "Start Me Up"): "122",
    ("Blur", "Song 2"): "130",
    ("Jimi Hendrix", "Purple Haze"): "108",
    ("Brad Sucks", "Borderline"): "120",
    ("John Frusciante", "Carvel"): "96",
    ("Stevie Ray Vaughan", "Pride and Joy"): "125",
    ("ZZ Top", "La Grange"): "81",
    ("Led Zeppelin", "Rock and Roll"): "170",
    ("Led Zeppelin", "Fool in the Rain"): "130",
    ("Toto", "Rosanna"): "88 / 176",
    ("Steely Dan", "Home At Last"): "118",
    ("Steely Dan", "Babylon Sisters"): "117",
    ("ZZ Top", "Tush"): "146",
    ("Boz Scaggs", "Lido Shuffle"): "116",
    ("The Police", "Walking on the Moon"): "146",
    ("Jimi Hendrix", "Red House"): "67",
    ("James Brown", "Sex Machine"): "108",
    ("Red Hot Chili Peppers", "Give It Away"): "92",
    ("Stevie Wonder", "Superstition"): "100",
    ("The Meters", "Cissy Strut"): "90",
    ("Mark Ronson feat. Bruno Mars", "Uptown Funk"): "115",
    ("Parliament", "Give Up the Funk"): "107",
    ("Tower of Power", "What Is Hip?"): "112",
    ("The Meters", "Look-Ka Py Py"): "89",
    ("Prince", "Kiss"): "111",
    ("Chic", "Good Times"): "110",
    ("Red Hot Chili Peppers", "Can't Stop"): "91",
    ("Alabama Shakes", "Future People"): "105",
    ("Bee Gees", "Stayin' Alive"): "104",
    ("Chic", "Le Freak"): "119",
    ("Daft Punk feat. Pharrell Williams", "Get Lucky"): "116",
    ("Justin Timberlake", "Can't Stop the Feeling!"): "113",
    ("The Weeknd", "Blinding Lights"): "171",
    ("Donna Summer", "I Feel Love"): "128",
    ("Michael Jackson", "Billie Jean"): "117",
    ("Daft Punk", "One More Time"): "123",
    ("Robin S", "Show Me Love"): "122",
    ("Duke Ellington", "Take the A Train"): "160",
    ("Frank Sinatra", "Fly Me to the Moon"): "118",
    ("Frank Sinatra", "All of Me"): "130",
    ("Duke Ellington", "Satin Doll"): "120",
    ("Benny Goodman", "Sing, Sing, Sing"): "190",
    ("Miles Davis", "So What"): "136",
    ("Art Blakey", "Moanin'"): "128",
    ("Stan Getz & Joao Gilberto", "The Girl from Ipanema"): "130",
    ("Antonio Carlos Jobim", "Corcovado"): "120",
    ("Antonio Carlos Jobim", "Desafinado"): "145",
    ("Sergio Mendes & Brasil '66", "Mas Que Nada"): "96",
    ("Sergio Mendes", "Magalenha"): "126",
    ("Bob Marley & The Wailers", "Three Little Birds"): "74",
    ("Bob Marley & The Wailers", "No Woman No Cry"): "78",
    ("Bob Marley & The Wailers", "Is This Love"): "122",
    ("Bob Marley & The Wailers", "Could You Be Loved"): "103",
    ("UB40", "Red Red Wine"): "90",
    ("Fela Kuti", "Water No Get Enemy"): "107",
    ("Fela Kuti", "Zombie"): "118",
    ("Dave Brubeck Quartet", "Take Five"): "174",
    ("Pink Floyd", "Money"): "124",
    ("Tool", "Schism"): "108",
    ("Rush", "Tom Sawyer"): "88",
    ("Haken", "Puzzle Box"): "118",
    ("The Mars Volta", "Goliath"): "105",
    ("The Temptations", "My Girl"): "106",
    ("Marvin Gaye & Tammi Terrell", "Ain't No Mountain High Enough"): "130",
    ("Marvin Gaye", "I Heard It Through the Grapevine"): "117",
    ("Stevie Wonder", "Signed, Sealed, Delivered I'm Yours"): "108",
    ("The Supremes", "You Can't Hurry Love"): "97",
    ("Santana", "Oye Como Va"): "129",
    ("Lou Bega", "Mambo No. 5"): "174",
    ("Johnny Cash", "Folsom Prison Blues"): "110",
    ("Johnny Cash", "Ring of Fire"): "104",
    ("Alan Jackson", "Chattahoochee"): "172",
    ("Brooks & Dunn", "Boot Scootin' Boogie"): "131",
    ("The Specials", "A Message to You Rudy"): "104",
    ("Toots & The Maytals", "Monkey Man"): "152",
    ("Madness", "One Step Beyond"): "154",
    ("The Beat", "Mirror in the Bathroom"): "165",
    ("Rancid", "Salvation"): "180",
    ("Vavamuffin", "Bless"): "150",
    ("Robin S", "Show Me Love"): "122",
    ("CeCe Peniston", "Finally"): "120",
    ("Daft Punk", "One More Time"): "123",
    ("Stardust", "Music Sounds Better With You"): "124",
    ("The Shapeshifters", "Lola's Theme"): "124",
    ("The Roots", "The Seed (2.0)"): "98",
    ("Talib Kweli", "Get By"): "90",
    ("Kendrick Lamar", "Alright"): "110",
    ("D'Angelo", "Untitled (How Does It Feel)"): "76",
    ("The Pharcyde", "Runnin'"): "94",
    ("People Under the Stairs", "Acid Raindrops"): "88",
    ("Paktofonika", "Ja to Ja (Feat. Gutek)"): "92",
    ("Taco Hemingway", "Deszcz na betonie"): "90",
    ("Kendrick Lamar", "i"): "122",
    ("Plan B", "Stay Too Long"): "94",
    ("Miles Davis", "All Blues"): "138",
    ("John Coltrane", "My Favorite Things"): "180",
    ("Wayne Shorter", "Footprints"): "130",
    ("Mongo Santamaria", "Afro Blue"): "120",
    ("Duke Ellington", "Caravan"): "116",
    ("Horace Silver", "Song for My Father"): "126",
}


LOCAL_ALLOW = {
    ("Drums Groove 01 - Rock 8th Notes", "Jimi Hendrix", "Purple Haze"): "OK: rockowy numer z prostym, mocnym pulsem; nie jest seedem dla absolutnych podstaw, ale nadaje sie jako Twoj lokalny wariant.",
    ("Drums Groove 01 - Rock 8th Notes", "Brad Sucks", "Borderline"): "OK: znaleziony lokalny oryginal zamiast Psy Craft remixu; traktuj jako indie-rock straight feel.",
    ("Drums Groove 01 - Rock 8th Notes", "Blur", "Song 2"): "OK: prosty rockowy power groove, dobry do kontroli energii i wejsc.",
    ("Drums Groove 01 - Rock 8th Notes", "John Frusciante", "Carvel"): "OK: alternatywny rock; spokojniejsze cwiczenie rownych osemek.",
    ("Drums Groove 02 - Shuffle", "Jimi Hendrix", "Red House"): "OK: wolny bluesowy shuffle/12-8 feel; lepszy lokalny kandydat niz Purple Haze.",
    ("Drums Groove 03 - Funk", "Red Hot Chili Peppers", "Can't Stop"): "OK: funk-rock, dobry do ghost-note discipline i rownego pocketu.",
    ("Drums Groove 03 - Funk", "Alabama Shakes", "Future People"): "OK-ish: soul/funk-rock feel, zostawione jako osobisty wariant, nie jako czysty James Brown funk.",
    ("Drums Groove 10 - Odd Meters 5/4, 7/8", "Puscifer", "The Remedy"): "OK-ish: prog/alt-rock candidate; przed finalnym cwiczeniem sprawdz metrum sekcji.",
    ("Drums Groove 10 - Odd Meters 5/4, 7/8", "Haken", "Puzzle Box"): "OK: prog-metal/odd-meter practice material.",
    ("Drums Groove 10 - Odd Meters 5/4, 7/8", "The Mars Volta", "Goliath"): "OK: prog-rock z przesunieciami i duza energia.",
    ("Drums Groove 10 - Odd Meters 5/4, 7/8", "The Mars Volta", "Wax Simulacra"): "OK: prog-rock, przydatny do liczenia grup i akcentow.",
    ("Drums Groove 17 - Country Train Beat", "Blitzen Trapper", "Sleepytime in the Western World"): "OK-ish: alt-country lokalny wariant; nie klasyczny train beat.",
    ("Drums Groove 19 - Ska", "Rancid", "Salvation"): "OK: ska-punk, szybki offbeat i rowny hi-hat.",
    ("Drums Groove 19 - Ska", "Vavamuffin", "Bless"): "OK: reggae/ska z lokalnej bazy, pasuje do offbeat feel.",
    ("Drums Groove 22 - Hip-Hop", "People Under the Stairs", "Acid Raindrops"): "OK: hip-hop pocket, dobra praca z laid-back feel.",
    ("Drums Groove 22 - Hip-Hop", "Paktofonika", "Ja to Ja (Feat. Gutek)"): "OK: lokalny hip-hop pocket.",
    ("Drums Groove 22 - Hip-Hop", "Taco Hemingway", "Deszcz na betonie"): "OK: lokalny rap/hip-hop; cwicz minimalizm i timing.",
    ("Drums Groove 22 - Hip-Hop", "Kendrick Lamar", "i"): "OK-ish: hip-hop/funk/jazz rap crossover, dobry do feelu.",
    ("Drums Groove 22 - Hip-Hop", "Plan B", "Stay Too Long"): "OK-ish: UK hip-hop/rock crossover; nie traktuj jako czystego boom-bapu.",
}


BAD_TERMS = {
    "psy": "psy/trance/remix context, not a reliable acoustic drum groove candidate",
    "trance": "trance context, not the requested drum groove",
    "dubstep": "dubstep tag, not reggae/dub/hip-hop drum practice",
    "liquid funk": "liquid funk is drum and bass, not funk groove",
    "drum and bass": "drum and bass context, not this groove bucket",
    "dnb": "drum and bass context, not this groove bucket",
    "jazzstep": "jazzstep is DnB-adjacent, not swing/bossa/jazz waltz",
    "reggaeton": "reggaeton tag, not reggae one-drop/ska/dub",
}


def normalize_title(artist: str, title: str, section: str) -> tuple[str, str, str]:
    if artist == "Brad Sucks" and title == "Broder Line (Psy Craft Rmx)" and section == "Drums Groove 01 - Rock 8th Notes":
        return artist, "Borderline", "Replaced remix with local original: Brad Sucks - Borderline (18 Last.fm plays)."
    return artist, title, ""


def parse_rows() -> list[Row]:
    rows: list[Row] = []
    section = ""
    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## Drums Groove"):
            section = raw.removeprefix("## ").strip()
            continue
        if not raw.startswith("|") or "| ---" in raw or "| Slot |" in raw:
            continue
        parts = [part.strip() for part in raw.strip("|").split("|")]
        if len(parts) < 11:
            continue
        rows.append(Row(section, parts[0], parts[1], parts[2], parts[3], parts[5], parts[9]))
    return rows


def section_groove(section: str) -> str:
    return section.split(" - ", 1)[1]


def bpm_for(row: Row) -> tuple[str, str]:
    value = BPM.get((row.artist, row.title))
    if value:
        return value, "approx/common"
    return SECTION_DEFAULT_BPM.get(section_groove(row.section), "100"), "practice fallback"


def verify(row: Row) -> tuple[str, str, str]:
    artist, title, replacement_note = normalize_title(row.artist, row.title, row.section)
    fixed = Row(row.section, row.slot, row.bucket, artist, title, row.tags, "18" if replacement_note else row.plays)
    if fixed.bucket != "Last.fm local":
        return "yes", "seed/reference", replacement_note or "Trusted seed/reference for this groove bucket."
    allow_note = LOCAL_ALLOW.get((fixed.section, fixed.artist, fixed.title))
    if allow_note:
        return "yes", "verified local", replacement_note + (" " if replacement_note else "") + allow_note
    haystack = f"{fixed.artist} {fixed.title} {fixed.tags}".casefold()
    for term, reason in BAD_TERMS.items():
        if term in haystack:
            return "no", "excluded", replacement_note + (" " if replacement_note else "") + f"Excluded: {reason}."
    if "remix" in haystack or " rmx" in haystack or "(rmx" in haystack:
        return "no", "excluded", replacement_note + (" " if replacement_note else "") + "Excluded: remix version; needs original-track verification before export."
    return "no", "needs ear check", replacement_note + (" " if replacement_note else "") + "Excluded for now: tag match is too broad; verify by ear or replace with a stronger popular reference."


def build() -> str:
    rows = parse_rows()
    out: list[str] = [
        "# Drum Groove Study Playlists - Verified Export Draft",
        "",
        "This is the Spotify-export draft after rejecting weak Last.fm tag matches. The original working file stays in `Docs/DrumGrooveStudyPlaylists.md`; use this file for playlist creation.",
        "",
        "Accuracy policy:",
        "",
        "- `Spotify Ready = yes` means the track can be used by the later Spotify exporter.",
        "- `Spotify Ready = no` means the row is retained as audit/context and should not be exported.",
        "- BPM values are practice-oriented approximations unless `BPM Source` says otherwise. They are good enough for playlist sorting and rehearsal prep, not a substitute for a chart, metronome check, or transcription.",
        "- Last.fm local rows are not accepted by tag alone. Remix, psy/trance, DnB/liquid funk, dubstep, reggaeton and generic jazz-hop matches are excluded unless explicitly verified.",
        "",
        "Research references used for the verification pass:",
        "",
        "- Drumeo basic beat overview: https://www.drumeo.com/beat/drum-beats-everyone-should-know/",
        "- Rosanna shuffle / half-time shuffle context: https://www.drumlessons.com/drum-lessons/misc-lessons/the-rosanna-shuffle/",
        "- Reggae one-drop explanation: https://tunableapp.com/rhythm/reggae-one-drop/",
        "- Liquid funk / liquid DnB classification: https://en.wikipedia.org/wiki/Liquid_drum_and_bass",
        "",
    ]
    by_section: dict[str, list[Row]] = {}
    for row in rows:
        by_section.setdefault(row.section, []).append(row)
    excluded_count = 0
    ready_count = 0
    for section, section_rows in by_section.items():
        groove = section_groove(section)
        out.extend(
            [
                f"## {section}",
                "",
                f"- Groove: {groove}",
                "- Export rule: only rows with `Spotify Ready = yes` go to Spotify.",
                "- Folder target later: `Drums: Grooves`.",
                "",
                "| Slot | Bucket | Artist | Title | Spotify Ready | BPM | BPM Source | Groove Fit | Tags / style | Last.fm plays | Notes |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
            ]
        )
        for row in section_rows:
            artist, title, _ = normalize_title(row.artist, row.title, row.section)
            fixed = Row(row.section, row.slot, row.bucket, artist, title, row.tags, "18" if artist == "Brad Sucks" and title == "Borderline" else row.plays)
            ready, fit, note = verify(row)
            bpm, source = bpm_for(fixed)
            if ready == "yes":
                ready_count += 1
            else:
                excluded_count += 1
            cells = [
                fixed.slot,
                fixed.bucket,
                fixed.artist,
                fixed.title,
                ready,
                bpm,
                source,
                fit,
                fixed.tags,
                fixed.plays,
                note,
            ]
            out.append("| " + " | ".join(cell.replace("|", "/") for cell in cells) + " |")
        out.append("")
    out.extend(
        [
            "## Verification Summary",
            "",
            f"- Spotify-ready rows: {ready_count}",
            f"- Excluded / needs-ear-check rows kept for audit: {excluded_count}",
            "- Main fix: local Last.fm candidates are now opt-in verified instead of tag-heuristic `yes`.",
            "- Brad Sucks fix: `Broder Line (Psy Craft Rmx)` was replaced only in the rock section with local original `Borderline`; the remix remains excluded everywhere else.",
            "- Funk fix: `liquid funk` rows are excluded because liquid funk is a drum-and-bass subgenre, not funk drumming.",
            "",
        ]
    )
    return "\n".join(out)


def main() -> int:
    TARGET.write_text(build(), encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
