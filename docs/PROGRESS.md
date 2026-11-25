# PROGRESS

Claude Code updates this file at the end of every stage. Status values: `todo`, `in progress`, `waiting`, `blocked`, `done`.

| Stage | Name | Status | Date finished | Key artifacts | Notes / blockers |
|---|---|---|---|---|---|
| S00 | Setup and scaffolding | done | 2026-11-25 | `pyproject.toml`, `src/bgllog/io.py`, `configs/`, `requirements.lock.txt`, `docs/notes/S00-setup.md` | 20 tests pass; repo public in DM-FP26 |
| S01 | Data acquisition + EDA | done | 2026-11-25 | `scripts/s01_download_and_eda.py`, `src/bgllog/parsing.py`, `reports/tables/*`, `reports/figures/eda_*.png`, `docs/notes/S01-data-and-eda.md` | 27 tests pass; counts match published figures exactly |
| S02 | Preprocessing | done | 2026-11-25 | `scripts/s02_preprocess.py`, `src/bgllog/windows.py`, `data/processed/templates.csv`, `artifacts/drain3_state.bin`, `artifacts/vocab.json`, `handoff/windows.npz`, notes (ID + EN) | 396 templates, 474,795 windows; test split has 60.5% UNK tokens (concept drift), see decisions |
| S03 | Pattern mining | done | 2026-11-25 | `scripts/s03_patterns.py`, `src/bgllog/patterns.py`, `reports/tables/{frequent_itemsets,association_rules,sequential_patterns_prealert,pattern_examples}.csv`, `artifacts/patterns/*`, `reports/figures/pat_*.png`, notes (ID + EN) | 606 P + 606 C windows, 83 rules, 293 sequences; 4 honesty checks pass; low recall |
| S04 | Training code + handoff package | done | 2026-11-25 | `src/bgllog/{models,train,embed}.py`, `scripts/{train,check_gpu,s04_make_handoff}.py`, `scripts/train_all.ps1`, `docs/GPU-HANDOFF-FRIEND.md`, notes (ID + EN) | 43 tests pass; train_all.ps1 untested on Windows; GPU teammate account still to confirm |
| S05 | GPU hand-off, merge, embeddings | waiting | | | waits for teammate pushing `gpu-run` |
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
| 2026-11-25 | S03 | Dropped pre-alert windows that contain alert lines from an earlier burst (214 of 820); itemset size capped at 4; C support counted directly; added time-matched-control and 70/30 temporal hold-out checks | Avoid circular mining; keep rules readable; a suspected time confound had to be tested (it did not hold up) |
| 2026-11-25 | S04 | Added baseline `repeat_last` and metric `top1_on_changes`; test metrics written for all windows AND UNK-free windows | Plain top-1 is inflated by repetition (repeat-last already scores 94 to 96%) |
| 2026-11-25 | S04 | Manual batching instead of a DataLoader | Whole train set fits on the device (53 MB); avoids Windows worker issues |
| 2026-11-25 | S02 | Added mask `HEXW` (bare hex words) and `NUM`; Drain3 fed unique messages only | 630 singleton templates before HEXW; unique-only is equivalent and about 20 s |
| 2026-11-25 | S02 | Test split has 60.5% UNK tokens (only 25,356 UNK-free test windows, 1,056 with alerts). Kept the spec split; **report test metrics on all windows AND on the UNK-free subset** | Concept drift: new event types after the train period. Revisit (evaluate on val, or blocked folds) only if the UNK-free subset is too small in S06/S07 |
| 2026-11-25 | S01 | BGL.zip already downloaded and extracted to `data/raw/` during planning. Line count 4,747,963 and alert count 348,460 match the expected figures exactly | Early inspection; S01 still has to run its own audit and write results.json |

## Next action

Waiting on the GPU teammate (S05). Send them `docs/GPU-HANDOFF-FRIEND.md` and the repo URL; confirm their GitHub account (Bima-031 has write access, najwarjombi did not at last check). Meanwhile: draft the S01 to S03 report chapters (S09 skeleton), or train on CPU here if Nafi prefers (about 150 s per epoch). When the teammate says "pushed", run S05.
