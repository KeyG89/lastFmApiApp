This project follows `project-builder-flow`. Start with `MasterPlan.md`, then the active file in `Items/`.

For Last.fm, Spotify, Shazam, database, report, or playlist work, load `.agents/skills/lastfm-spotify-operator/SKILL.md` and the setup or operations reference it selects. Use `Docs/AgentOperations.md` when handing the repository to a new developer or an agent that does not discover repository skills automatically.

Validate operational changes with:

```bash
.venv/bin/python Diagnostics/integration_doctor.py .
bash Diagnostics/check.sh
```
