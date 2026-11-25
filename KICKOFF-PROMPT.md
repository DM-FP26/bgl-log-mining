# Kickoff prompt for Claude Code

Open Claude Code in the project folder (the one that contains `CLAUDE.md` and `docs/`) and paste:

```
Read CLAUDE.md, then docs/00-overview.md, docs/01-requirements-traceability.md, docs/02-environment-windows.md and docs/03-conventions-and-contracts.md.
Then execute stage S00 exactly as specified in docs/stages/S00-setup.md.
Work stage by stage. At the end of each stage: make the checks pass, write the note, update docs/PROGRESS.md, commit.
Stop and ask me only under the stop-and-ask rules in CLAUDE.md, and at the GPU hand-off (S04 to S05).
```

When Claude Code stops at S05 ("waiting for teammate"):

1. Send your teammate the repo link and `docs/GPU-HANDOFF-FRIEND.md` (Claude Code prints a ready-to-send message at the end of S04).
2. When he says "pushed", tell Claude Code: `The teammate pushed gpu-run. Continue S05.`

If you want it to keep going while waiting: `While I wait for the GPU run, continue S03 and draft the report chapters for S01 to S03.`
