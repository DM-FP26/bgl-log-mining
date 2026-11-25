# PROGRESS

Claude Code updates this file at the end of every stage. Status values: `todo`, `in progress`, `waiting`, `blocked`, `done`.

| Stage | Name | Status | Date finished | Key artifacts | Notes / blockers |
|---|---|---|---|---|---|
| S00 | Setup and scaffolding | done | 2026-11-25 | `pyproject.toml`, `src/bgllog/io.py`, `configs/`, `requirements.lock.txt`, `docs/notes/S00-setup.md` | 20 tests pass; repo public in DM-FP26 |
| S01 | Data acquisition + EDA | done | 2026-11-25 | `scripts/s01_download_and_eda.py`, `src/bgllog/parsing.py`, `reports/tables/*`, `reports/figures/eda_*.png`, `docs/notes/S01-data-and-eda.md` | 27 tests pass; counts match published figures exactly |
| S02 | Preprocessing | todo | | | |
| S03 | Pattern mining | todo | | | |
| S04 | Training code + handoff package | todo | | | |
| S05 | GPU hand-off, merge, embeddings | todo | | | waits for teammate pushing `gpu-run` |
| S06 | Clustering | todo | | | |
| S07 | Evaluation + analysis | todo | | | |
| S08 | Streamlit app | todo | | | |
| S09 | Report draft + defense pack + final check | todo | | | |
| S10 | Presentation slides (lecturer addition) | todo | | | after S08; needs Nafi's .pptx template. See `docs/04-lecturer-additions.md` |
| S11 | Break-it-on-purpose demos, one per student (lecturer addition) | todo | | | scenarios chosen by Nafi after S08. See `docs/04-lecturer-additions.md` |

## Decisions log

Record every deviation from the specs here (date, stage, what, why).

| Date | Stage | Decision | Reason |
|---|---|---|---|
| 2026-11-25 | S00 | GitHub repo is **public** (`DM-FP26/bgl-log-mining`), not private as the spec said | Nafi decided a public student project is fine |
| 2026-11-25 | S00 | Repo lives in `~/projects/bgl-log-mining` on Linux, Python 3.12 venv via `uv`; torch from the PyTorch **CPU** index | Spec assumed Windows; Nafi's machine only needs CPU torch (no CUDA, no multi-GB wheel) |
| 2026-11-25 | S00 | Git commits use the GitHub noreply email | The repo is public, so the author email would be visible to everyone |
| 2026-11-25 | all | Added S10 (slides) and S11 (break-it-on-purpose demos) | Lecturer's new requirements; details in `docs/04-lecturer-additions.md` |
| 2026-11-25 | S01 | `--sample` offset set to 3,000,000 in config; parser tolerates a missing node-repeat field and empty messages | Real data differs from the assumed layout (324 lines lack the repeat field; 34,470 messages are empty) |
| 2026-11-25 | S01 | BGL.zip already downloaded and extracted to `data/raw/` during planning. Line count 4,747,963 and alert count 348,460 match the expected figures exactly | Early inspection; S01 still has to run its own audit and write results.json |

## Next action

S02: parse to Drain3 templates (apply masks, check the template count stays in the hundreds to low thousands), build windows of 20 with step 10, chronological split. Watch out for two S01 findings: (1) alerts are extremely bursty (one node = 43.7% of alerts, June 2005 = 64.6%), so train/test alert ratios will differ, so report window-level ratios per split; (2) 8 corrupted lines have junk in `type`/`component`/`level` (see `reports/tables/field_values.csv`); decide how to treat them and record it.
