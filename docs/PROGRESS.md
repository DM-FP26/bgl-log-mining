# PROGRESS

Claude Code updates this file at the end of every stage. Status values: `todo`, `in progress`, `waiting`, `blocked`, `done`.

| Stage | Name | Status | Date finished | Key artifacts | Notes / blockers |
|---|---|---|---|---|---|
| S00 | Setup and scaffolding | done | 2026-11-25 | `pyproject.toml`, `src/bgllog/io.py`, `configs/`, `requirements.lock.txt`, `docs/notes/S00-setup.md` | 20 tests pass; repo public in DM-FP26 |
| S01 | Data acquisition + EDA | todo | | | |
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
| 2026-11-25 | S01 | BGL.zip already downloaded and extracted to `data/raw/` during planning. Line count 4,747,963 and alert count 348,460 match the expected figures exactly | Early inspection; S01 still has to run its own audit and write results.json |

## Next action

S01: run `scripts/s01_download_and_eda.py` (BGL.log is already in `data/raw/`, so skip the download), parse all lines, write the dirty-data audit and EDA figures. Known from early inspection (re-measure properly in S01): about 34k lines have an empty message, 306 lines have `-` or `NULL` as node, and `FATAL` level is not the same as the alert label.
