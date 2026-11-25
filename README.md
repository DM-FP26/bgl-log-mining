# BGL Log Mining: Data Mining Final Project

Clustering and pattern mining of Blue Gene/L supercomputer logs (Loghub) using LSTM/GRU sequence embeddings, with a Streamlit demo.

- **Plan and specs:** `docs/` (start at `docs/00-overview.md`)
- **Standing orders for Claude Code:** `CLAUDE.md`
- **Progress:** `docs/PROGRESS.md`
- **Report (Indonesian) skeleton:** `docs/report-skeleton-id.md`
- **Defense prep for the team (Indonesian):** `docs/defense-pack-id.md`

## Quick start (Windows, PowerShell)

```powershell
git clone <repo-url>
cd <repo>
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

The demo only needs the small artifacts that are committed under `artifacts/`. Rebuilding the data from scratch is covered by the stage specs.

## Dataset and citation

BGL logs come from Loghub (Zhu, He, He, Liu, Lyu, "Loghub: A Large Collection of System Log Datasets for AI-driven Log Analytics", IEEE ISSRE 2023). See `docs/references.md`.
