# MasterPlan: Last.fm API App

Last.fm API App turns personal scrobbles into a trustworthy local music memory.
Build the data foundation first, then use it for playlists, genre maps, and discovery tools.

## Project Items

| Item | Title | Status | File | Commit Prefix |
| --- | --- | --- | --- | --- |
| 1 | Last.fm Importer Alpha | Done | [T.1-alpha-version.md](Items/T.1-alpha-version.md) | `[T.1]` |
| 2 | Playlist Intelligence Reports | Open | [T.2-alpha-additions.md](Items/T.2-alpha-additions.md) | `[T.2]` |
| 3 | Diagnostics And Test Harness | Done | [T.3-diagnostics-and-test-harness.md](Items/T.3-diagnostics-and-test-harness.md) | `[T.3]` |
| 4 | Documentation And Developer Tutorial | Done | [T.4-documentation-and-developer-tutorial.md](Items/T.4-documentation-and-developer-tutorial.md) | `[T.4]` |
| 5 | Spotify Playlist Export | In Progress | [T.5-deployment-and-release-path.md](Items/T.5-deployment-and-release-path.md) | `[T.5]` |
| 6 | Spotify Safety And Account Mirror | In Progress | [T.6-spotify-safety-and-account-mirror.md](Items/T.6-spotify-safety-and-account-mirror.md) | `[T.6]` |
| 7 | Shazam Library Integration | In Progress | [T.7-shazam-library-integration.md](Items/T.7-shazam-library-integration.md) | `[T.7]` |
| 8 | Current Music Discovery Expander | Open | [T.8-current-music-discovery-expander.md](Items/T.8-current-music-discovery-expander.md) | `[T.8]` |
| 9 | Drum Groove Study Playlists | In Progress | [T.9-drum-groove-study-playlists.md](Items/T.9-drum-groove-study-playlists.md) | `[T.9]` |

## AI Augmentations

- Add decay-weighted reports that distinguish music loved now from music loved historically.
- Add Spotify matching/export once the local Last.fm library is reliable.
- Keep Shazam as a separate discovery inbox that can be linked to Last.fm and Spotify when matches are available.
- Add discovery surfaces later: music channels, instrumental breakdowns, and recommendation research.
- Treat unknown Spotify playlist creation dates as protected until proven app-created after 2026-05-31.

## Workflow Improvements

- This project was created with `project-builder-flow`.
- If the user points to a workflow/template/agent-instruction improvement, follow `AGENTS.md` and `Docs/AutoImprovement.md`.
- Create or update a `project-builder-flow` MasterPlan item, implement the change in that source repo, and open a PR with a detailed functionality description.
