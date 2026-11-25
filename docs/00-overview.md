# 00. Overview

## 1. Decisions that are locked

| Topic | Decision |
|---|---|
| Course deliverable | Data Mining final project (FP), group of 5 |
| Dataset | **BGL** from Loghub (Blue Gene/L supercomputer log). Raw, unstructured text. Zenodo download. |
| Task | **Clustering + pattern mining** (not supervised classification). Alert labels are used only to *validate* clusters and patterns. |
| Deep learning | **LSTM and GRU** sequence models (next-event prediction); window embeddings feed the clustering |
| Compute | Teammate's Windows laptop with an RTX 5060 for training only. Everything else runs on CPU on Nafi's machine. |
| App | **Streamlit** demo (the "deploy model" requirement) |
| Language | Code and docs in English. Report, `docs/notes/*`, defense pack in Indonesian. |
| Repo | Private GitHub repo created with `gh`. Teammate pushes to branch `gpu-run`. |
| AI use | The lecturer allows AI assistance. |

## 2. What we are building (one picture)

```
Zenodo BGL.zip
   │  S01  download, inspect, EDA
   ▼
BGL.log (≈4.75M lines, raw text, "dirty")
   │  S02  parse fields → Drain3 templates (event IDs) → sliding windows → chronological split
   ▼
windows (N × 20 event IDs) + metadata (alert flags, tags)
   ├─ S03 pattern mining: FP-Growth, association rules, PrefixSpan  (pre-alert vs control windows)
   │
   ├─ S04 prepare LSTM/GRU training code + handoff package ──┐
   │                                                          │  S05  GPU laptop trains, pushes `gpu-run`
   │                                                          ▼
   │                                       weights + curves + metrics  → merge, extract embeddings (CPU)
   ▼
S06 clustering (K-Means, HDBSCAN) on embeddings vs. baselines (bag-of-events, TF-IDF+SVD)
   ▼
S07 evaluation + analysis → reports/results.json (single source of truth)
   ▼
S08 Streamlit app          S09 report draft (ID) + defense pack (ID) + final checks
```

## 3. Stage list and dependencies

| Stage | Name | Needs | Can overlap with |
|---|---|---|---|
| S00 | Setup and scaffolding | n/a | n/a |
| S01 | Data acquisition + EDA | S00 | n/a |
| S02 | Preprocessing | S01 | n/a |
| S03 | Pattern mining | S02 | S04, S05 (while waiting for GPU) |
| S04 | Training code + handoff package | S02 | S03 |
| S05 | GPU hand-off, merge, embeddings | S04 + teammate | S03, report drafting |
| S06 | Clustering | S05 | n/a |
| S07 | Evaluation + analysis | S03, S06 | n/a |
| S08 | Streamlit app | S07 | report drafting |
| S09 | Report draft + defense pack + final check | S07, S08 | n/a |

## 4. Repository layout (target)

```
.
├─ CLAUDE.md
├─ README.md
├─ requirements.txt            requirements-train.txt   requirements.lock.txt
├─ configs/                    default.yaml   train.yaml
├─ src/bgllog/                 io.py parsing.py windows.py patterns.py models.py train.py embed.py
│                              clustering.py evaluate.py viz.py infer.py
├─ scripts/                    s01_download_and_eda.py s02_preprocess.py s03_patterns.py
│                              s04_make_handoff.py s05_extract_embeddings.py s06_cluster.py
│                              s07_evaluate.py s08_app_selftest.py s09_build_report_data.py
│                              check_gpu.py train.py train_all.ps1
├─ app/                        streamlit_app.py
├─ tests/
├─ data/                       raw/ (ignored)  interim/ (ignored)  processed/ (small csv only)
├─ artifacts/                  small committed artifacts (see 03-conventions)
├─ handoff/                    windows.npz  results/ (filled by the GPU teammate)
├─ reports/                    figures/  tables/  results.json  laporan-draft.md
└─ docs/                       this blueprint + notes/
```

## 5. Why this design (so you can defend choices)

- **Clustering + pattern mining** matches the course vocabulary (data mining) and the data (unstructured, mostly unlabeled structure). Labels exist, which lets us *check* the clusters honestly with NMI/ARI.
- **Event IDs via Drain3** turn free text into a small vocabulary an LSTM/GRU can model.
- **Next-event prediction** needs no labels. The hidden state of the sequence model becomes the "fingerprint" (embedding) of a window.
- **Chronological split** prevents leakage between overlapping windows from the same time period.
- **Baselines** (bag-of-events, TF-IDF+SVD) show whether deep embeddings add value. If they do not, we report that honestly.
- **Only weights travel to the GPU laptop** (small files), so the hand-off is one `git clone`, one command, one `git push`.

## 6. Known risks

1. **Class imbalance and alert bursts.** Alerts are rare at line level (about 7% of lines per published statistics) and clustered in time. Report window-level ratios, not only line-level.
2. **Drain3 template explosion** if masking is poor. Target: a few hundred to low thousands of templates, not tens of thousands.
3. **Memory.** 4.75M lines: process in chunks and store compact dtypes.
4. **Blackwell GPU + PyTorch.** Needs a CUDA 12.8+ PyTorch build. See `02-environment-windows.md`.
5. **Windows sleep or battery throttling** during training. Handled in the hand-off guide (plug in, no sleep, resume support).
