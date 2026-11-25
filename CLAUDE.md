# CLAUDE.md: standing orders for Claude Code

Project: **BGL log mining**, a university Data Mining final project (FP).
You are the executing engineer. A human (Nafi) owns decisions. The blueprint in `docs/` owns the plan.
Read this file at the start of every session, then read `docs/PROGRESS.md` to see where we are.

## 1. Mission

Take the Blue Gene/L (BGL) supercomputer logs from Loghub. Turn the raw, unstructured log text into event sequences. Learn sequence embeddings with LSTM/GRU. Cluster the embeddings. Mine frequent patterns that precede alerts. Evaluate honestly. Ship:

1. a Streamlit demo (the "deploy model" requirement),
2. clean source code in this repo,
3. every number, figure and table the Indonesian report needs, plus a defense pack so all five team members can explain the project.

## 2. Read order

1. `docs/00-overview.md`
2. `docs/01-requirements-traceability.md`
3. `docs/02-environment-windows.md`
4. `docs/03-conventions-and-contracts.md`
5. `docs/04-lecturer-additions.md` (two extra lecturer requirements: slides = S10, break-it-on-purpose demos = S11)
6. The spec of the stage you are about to run: `docs/stages/Sxx-*.md`
7. `docs/references.md` (whenever you write anything that cites papers)

## 3. Working rules

1. **Order.** Run stages S00 → S09. `00-overview.md` says which stages may overlap.
2. **Specs are firm about outputs and checks, loose about tuning.** If the data contradicts a default (for example the template count explodes), fix the cause, record it in the stage note, move on.
3. **Every stage ends with all four of these:**
   a. every "Definition of done" check passes,
   b. two notes: `docs/notes/Sxx-<name>.md` in **simple Indonesian** (for the team and presentation) and `docs/notes/en/Sxx-<name>.md` in **English, technical, step by step** (for internal use); format in `docs/notes/README.md`,
   c. `docs/PROGRESS.md` updated,
   d. a git commit `Sxx: <what>`.
4. **Never fabricate numbers.** Every number in notes, report draft or app comes from a file under `artifacts/` or `reports/`. `reports/results.json` is the single source of truth.
5. **Reproducible.** Seed 42 from config. Scripts are idempotent (cache outputs, `--force` recomputes). Every script has `--sample` for a fast run.
6. **Data hygiene.** Never commit `data/raw`, `data/interim` or parquet files. Only the small artifacts listed in `docs/03-conventions-and-contracts.md` get committed.
7. **Windows-first.** Use `pathlib`; read logs as UTF-8 with `errors="replace"`; guard entry points with `if __name__ == "__main__":`; `num_workers=0` in DataLoader; give PowerShell commands in docs.
8. **Stop and ask** (write the question to `docs/BLOCKERS.md` and tell Nafi in chat) when: the scope changes; the download is blocked; the dataset counts differ from expected by more than 1%; anything needs credentials or money; you would delete user files or force-push.
9. **Keep it simple.** Plain scripts plus a small package `src/bgllog/`. No Hydra, MLflow, or Docker.
10. **Tests.** Light pytest: parsing, windowing and labeling, split leakage, plus one tiny end-to-end smoke test on a 2,000-line sample.
11. **Lecturer additions.** S10 (slides, from Nafi's .pptx template) and S11 (each of 5 students breaks one phase on purpose) come after S08. Do not pick the S11 scenarios yourself; Nafi decides. While building S01 to S08, keep choices in config flags so a phase can be switched off cleanly (details in `docs/04-lecturer-additions.md`).
12. **Language.** Code, comments, commit messages, docs: English. Notes in `docs/notes/` exist in both languages (Indonesian for presentation, `docs/notes/en/` for internal); the report draft and the defense pack: Indonesian.

## 4. The GPU hand-off (the one human-in-the-loop moment)

Training the LSTM/GRU happens on a teammate's laptop (Windows, RTX 5060). You prepare everything in S04, then stop at S05 until the teammate has pushed branch `gpu-run`. Details: `docs/stages/S04-*.md`, `docs/stages/S05-*.md`, `docs/GPU-HANDOFF-FRIEND.md`.
While waiting you MAY continue S03 (pattern mining) and the S01–S03 parts of the report draft.

## 5. Commands cheat sheet (PowerShell, from repo root)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python scripts/s01_download_and_eda.py --sample
streamlit run app/streamlit_app.py
```

(Exact script names are defined in each stage spec.)

## 6. The project is done when

- `docs/PROGRESS.md` shows S00–S09 complete,
- `pytest -q` passes,
- `streamlit run app/streamlit_app.py` works on a fresh clone using only committed artifacts,
- `reports/results.json`, `reports/figures/`, `reports/tables/`, `reports/laporan-draft.md` and `docs/defense-pack-id.md` exist and agree with each other,
- the final check in `docs/stages/S09-*.md` is ticked.
