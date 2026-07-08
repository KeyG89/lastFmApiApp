# Discovery Bangers 2026-07-08

## Goal

Create five Spotify playlists with 10 songs each that are not present in the local Last.fm database as exact `artist - title` pairs. The tracks should be broadly recognized or critically visible, not total underground, and should fit the user's established taste without drifting into throwaway radio filler.

## Local Taste Anchors

The local Last.fm profile leans heavily toward rock, alternative rock, electronic, indie rock, punk, psychedelic rock, funk, hip-hop, house, progressive rock, and harder guitar music. The strongest artist anchors include Red Hot Chili Peppers, Rancid, John Frusciante, Shpongle, Queens of the Stone Age, Jimi Hendrix, Astrix, Depeche Mode, Muse, Jet, Velvet Revolver, MGMT, Volbeat, Radiohead, Pendulum, The Prodigy, Fatboy Slim, Justice, The Hives, Led Zeppelin, The Mars Volta, Vavamuffin, and Paktofonika.

## Search Keys

- `best electronic tracks 2025 2026 Billboard Pitchfork Resident Advisor`
- `best EDM songs 2025 2026 Billboard Dancing Astronaut`
- `best house tracks 2025 2026 Resident Advisor Billboard`
- `best rock songs 2025 2026 Rolling Stone NME Pitchfork`
- `Billboard 50 best dance songs 2025 Disclosure Jamie xx Anyma John Summit`
- `Pitchfork 100 best songs 2024 2025 Fontaines DC Starburster Jamie xx Life`
- `Rolling Stone best songs 2024 2025 Fontaines DC Starburster Doechii Denial Is A River`
- `NME best songs 2025 Wolf Alice Bloom Baby Bloom Wet Leg`

## Source Signals

- Pitchfork 2024 best songs and readers poll for cross-genre critical visibility: https://pitchfork.com/features/lists-and-guides/best-songs-2024 and https://pitchfork.com/features/lists-and-guides/2024-readers-poll-results
- Billboard dance/electronic chart context and 2025/2026 dance visibility, especially for Anyma, Jamie xx, Disclosure, and dance-radio crossover tracks: https://www.billboard.com/charts/dance-electronic-songs/
- Fontaines D.C. `Starburster` recognition across major year-end lists and Grammy/alternative visibility: https://en.wikipedia.org/wiki/Starburster and https://pitchfork.com/reviews/albums/fontaines-dc-romance
- Wet Leg/Wolf Alice current rock visibility and 2025 album/single context: https://en.wikipedia.org/wiki/Catch_These_Fists and https://en.wikipedia.org/wiki/The_Clearing_(Wolf_Alice_album)
- Jamie xx `In Waves` release context and dance-floor reception: https://en.wikipedia.org/wiki/In_Waves_(Jamie_xx_album)
- Anyma/Ellie Goulding `Hypnotized` chart and dance-list visibility: https://en.wikipedia.org/wiki/Hypnotized_(Anyma_and_Ellie_Goulding_song)

## Selection Rules

- No exact local Last.fm scrobble match for `artist - title`.
- Known artists are allowed when the specific song is not in the local database.
- Prefer songs with at least one of: chart traction, major playlist traction, strong critical mentions, visible festival/club momentum, or broad listener recognition.
- Avoid total underground picks unless they have a strong reason to fit the user's taste.
- Avoid destructive Spotify operations. These are new playlists; older playlists were not deleted or overwritten.

## Local Database Validation

The final 50 candidates were checked against `data/lastfm.sqlite3` using exact case-insensitive artist/title joins. Earlier candidates that failed this rule were removed:

- `Jack White - That's How I'm Feeling`: 2 local scrobbles
- `Lola Young - Messy`: 1 local scrobble
- `Wet Leg - catch these fists`: 1 local scrobble
- `Jack White - Archbishop Harold Holmes`: 9 local scrobbles
- `Doechii - DENIAL IS A RIVER`: 6 local scrobbles

The final candidate set returned zero local scrobbles.

## Spotify Results

All Spotify dry-runs matched 50/50 tracks. All exports created private playlists and added 50/50 tracks.

### Discovery 2026: Electronic

URL: https://open.spotify.com/playlist/1VxKtfHdXEjswXMuLUy3Jo

Source file: `data/discovery-electronic-2026-07-08.txt`

Tracks:

1. Fred again.. - places to be
2. The Chemical Brothers - Live Again
3. Jamie xx - Life
4. Caribou - Honey
5. Justice - Neverender
6. Bonobo - Expander
7. Bicep - CHROMA 002 L.A.V.A
8. Four Tet - Loved
9. Floating Points - Del Oro
10. Underworld - Techno Shinkansen

### Discovery 2026: EDM

URL: https://open.spotify.com/playlist/5YETIUmK5MkKgILrcNNXu7

Source file: `data/discovery-edm-2026-07-08.txt`

Tracks:

1. Anyma - Hypnotized
2. deadmau5 - Science
3. Dom Dolla - Forever
4. John Summit - Shiver
5. Swedish House Mafia - Finally
6. Tiesto - Tantalizing
7. Armin van Buuren - Dream A Little Dream
8. SIDEPIECE - Cry For You
9. Kaskade - DNCR
10. David Guetta - Gone Gone Gone

### Discovery 2026: House

URL: https://open.spotify.com/playlist/6CC20aPSVFv8SwmsidKYRM

Source file: `data/discovery-house-2026-07-08.txt`

Tracks:

1. PAWSA - TOO COOL TO BE CARELESS
2. Mau P - BEATS FOR THE UNDERGROUND
3. Adam Port - Move
4. HUGEL - I Adore You
5. Peggy Gou - 1+1=11
6. Chris Stussy - Desire
7. BLOND:ISH - Never Walk Alone
8. RUFUS DU SOL - Music is Better
9. Gorgon City - Voodoo
10. ANOTR - How You Feel

### Discovery 2026: Rock

URL: https://open.spotify.com/playlist/5DBML8T9r4RfaR5q9hgrIB

Source file: `data/discovery-rock-2026-07-08.txt`

Tracks:

1. Fontaines D.C. - Starburster
2. The Last Dinner Party - Nothing Matters
3. IDLES - Dancer
4. The Warning - MORE
5. Yard Act - We Make Hits
6. The Smile - Friend of a Friend
7. Royal Blood - Pull Me Through
8. Queens of the Stone Age - Paper Machete
9. Linkin Park - The Emptiness Machine
10. Wolf Alice - Bloom Baby Bloom

### Discovery 2026: Various Songs

URL: https://open.spotify.com/playlist/6B40wxcBJkY8UUGQk1AVPL

Source file: `data/discovery-various-songs-2026-07-08.txt`

Tracks:

1. Hozier - Too Sweet
2. Billie Eilish - CHIHIRO
3. Chappell Roan - Good Luck, Babe!
4. Sam Fender - People Watching
5. The Cure - Alone
6. Mk.gee - Alesis
7. Magdalena Bay - Image
8. FKA twigs - Eusexua
9. Tyler, The Creator - Noid
10. Michael Kiwanuka - Floating Parade

## Feedback Capture Template

For each playlist, collect:

- Strong discoveries:
- Good but not urgent:
- Wrong vibe:
- Too obvious:
- Too obscure:
- Already known outside Last.fm:
- Artists to explore more:
- Artists to avoid:
