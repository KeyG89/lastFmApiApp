Automated tests live in this directory and are run by:

```bash
.venv/bin/python -m pytest -q
```

Current coverage focuses on Last.fm importer parsing, Spotify safety/rate-limit behavior, Shazam web CSV import, linking, playlist generation, Spotify export bookkeeping, and integration-readiness parsing/redirect validation.
