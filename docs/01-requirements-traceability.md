# 01. Requirements traceability

Source: lecturer's revised brief (Section 13, "FP Data Mining") plus the earlier dataset rules. Tick each row in S09.

## Revised brief (a–f)

| # | Requirement (paraphrased) | How we satisfy it | Stage | Evidence file | Done |
|---|---|---|---|---|---|
| a | Problem domain uses an unstructured or multimodal dataset | Raw BGL console log text (unstructured) | S01 | `reports/tables/dataset_summary.csv` | [ ] |
| b | At least 1000 samples for image/video, 5000 for text | About 4.75M log lines; about 475k windows | S01, S02 | `reports/tables/dataset_summary.csv`, `data/processed/windows_meta` row count in `reports/results.json` | [ ] |
| c | Deep learning allowed | LSTM + GRU next-event models | S04, S05 | `handoff/results/*/metrics.json` | [ ] |
| d | References from the last 5 years, international journals (IEEE or ScienceDirect) | 5 journal papers in `docs/references.md`, cited in report chapter II | S09 | `docs/references.md`, `reports/laporan-draft.md` | [ ] |
| e | Apply all DM stages: EDA, preprocessing, model training, testing and evaluation, results analysis | One stage group each (see below) | S01–S07 | notes + `reports/results.json` | [ ] |
| f1 | Visualized deployed model (e.g. Streamlit) | `app/streamlit_app.py` | S08 | app runs from fresh clone | [ ] |
| f2 | Report | Indonesian draft built from real results | S09 | `reports/laporan-draft.md` | [ ] |
| f3 | Source code | This repo | all | GitHub repo | [ ] |
| f4 | HKI (optional) | Out of scope | n/a | n/a | n/a |
| g | Presentation slides (added by lecturer 2026-11-25) | Fill Nafi's .pptx template from real results | S10 | `reports/slides/*.pptx` | [ ] |
| h | Each of 5 students breaks the project on purpose and demonstrates it (added 2026-11-25) | One scenario per student, own output folder | S11 | `reports/ablations/<scenario>/` | [ ] |

## "All DM stages" mapping (requirement e)

| DM stage | Where |
|---|---|
| EDA | S01 (and the dirty-data audit) |
| Preprocessing | S02 |
| Pattern mining | S03 |
| Model training | S04, S05 |
| Clustering | S06 |
| Testing and evaluation | S05 (DL test metrics), S06 and S07 (clustering and pattern evaluation) |
| Results analysis | S07 (error analysis, cluster profiles, limitations) |

## Earlier dataset rules (kept satisfied in case they still apply)

| Rule | Status |
|---|---|
| Unstructured data | Yes: raw log text |
| At least 100k records | Yes: about 4.75M lines |
| Dirty, messy data | Yes: Loghub logs are raw and unsanitized; the S01 audit documents the mess |
| Has a paper, not from Kaggle | Yes: Loghub, IEEE ISSRE 2023; hosted on Zenodo and GitHub |
| Found via Mendeley-like repositories | Zenodo is a research data repository; confirm with the lecturer if asked |

## Open item for the humans

- The Loghub paper is an IEEE **conference** paper. The lecturer asked for IEEE/ScienceDirect **journals**, so the five references counted for requirement (d) in `docs/references.md` are all journal articles. Loghub is cited additionally as the dataset source.
