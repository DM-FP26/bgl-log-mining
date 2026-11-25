# S08. Streamlit app (the "deploy model" deliverable)

## Goal
A simple, robust Streamlit app that lets someone explore the data insights, clusters and patterns, and try the model on log lines. It must run on a fresh clone with only committed artifacts, on CPU.

## Depends on
S07 (all artifacts final).

## Inputs (all committed)
`artifacts/drain3_state.bin`, `artifacts/vocab.json`, `artifacts/models/<chosen>/best.pt` + `config.json`, `artifacts/clusters/kmeans_<repr>.joblib` (+ scaler), `artifacts/clusters/cluster_profiles.json`, `artifacts/clusters/umap_sample.npz`, `artifacts/patterns/rules.csv`, `artifacts/patterns/seq_patterns.csv`, `artifacts/demo_samples.json`, `reports/results.json`, `reports/tables/*.csv`.

## Outputs
- `src/bgllog/infer.py`: the inference pipeline as plain functions, no Streamlit imports:
  `parse_lines(text) -> rows`, `to_event_ids(rows) -> ids` (Drain3 **match without learning**; unseen → UNK), `make_windows(ids, size, step)`, `embed(windows) -> array`, `assign_cluster(emb) -> (cluster_id, distance)`.
- `app/streamlit_app.py` and `app/README.md`.
- `scripts/s08_app_selftest.py`: loads the artifacts, runs the full inference on each item in `demo_samples.json`, and exits non-zero on any error.
- `tests/test_infer.py`.
- `artifacts/demo_samples.json`: at least 8 demo windows drawn from the **test** split (mix of alert and non-alert, different clusters), each stored as the raw log lines plus ground-truth alert tag (for display only).
- Screenshots `reports/figures/app_*.png` for the report (take them by running the app; if screenshots cannot be automated, list the exact manual steps in the note and leave a placeholder in the report).

## Pages (use `st.sidebar` radio or Streamlit multipage)

1. **Ringkasan (Overview).** Project title, dataset facts (from `results.json`), the pipeline in one picture, main result numbers. Indonesian UI text.
2. **Eksplorasi Data (EDA).** Show the key EDA figures with a selector.
3. **Cluster Explorer.** Plotly scatter from `umap_sample.npz` coloured by cluster or by alert (toggle); click or select a cluster to see its profile (size, alert rate, top alert tags, top templates, a representative window).
4. **Pola (Patterns).** Table of top association rules and sequential patterns with template text, filter by lift/support, small bar chart.
5. **Coba Model (Try it).**
   - Option A: pick one of the demo samples.
   - Option B: paste at least `window_size` raw BGL log lines (or upload a `.log`/`.txt`).
   - Output: parsed table (fields), template per line, event IDs (UNK highlighted), window embedding → **assigned cluster**, the distance to the centroid, the cluster's profile (alert rate, top tags), the matching mined patterns (if any pattern's items occur in the window), and a plain-language explanation line.
   - Clear error messages for too few lines or an unrecognised format.
6. **Tentang & Batasan.** Limitations (from `docs/limitations.md`), references list, team.

## Rules
- Cache heavy loads with `st.cache_resource` (models, Drain3 state, K-Means) and `st.cache_data` (tables).
- No internet access at runtime. No absolute paths. Paths relative to the repo root.
- Must work on CPU; Torch import should not require CUDA.
- Keep the UI simple and readable; it will be demoed on a projector: large fonts for key numbers, no more than two plots per page.
- All UI text in Indonesian. Code in English.

## Definition of done
- [ ] `python scripts/s08_app_selftest.py` passes.
- [ ] `streamlit run app/streamlit_app.py` starts and every page renders on a fresh clone (test in a temp clone, new venv, `pip install -r requirements.txt`).
- [ ] "Coba Model" returns a cluster for every demo sample and for a user-pasted block of lines.
- [ ] The page lists the same headline numbers as `reports/results.json` (read from the file, never typed in code).
- [ ] Screenshots captured or manual steps documented.

## Pitfalls
- Drain3 `add_log_message` **learns**; use the matching API (`match`) at inference so the app does not mutate templates. Verify with a test that the template count is unchanged after inference.
- Torch + Streamlit reload quirks: load the model inside a cached function.
- Streamlit's file watcher may complain about torch on Windows; if so set `server.fileWatcherType = "none"` in `.streamlit/config.toml` and commit it.
- Do not display raw hostnames or personal data beyond what is in the public dataset.

## Report hooks
Chapter IV.8 (Implementasi dan demo aplikasi) with the screenshots and a short description of each page.

## Note to write
`docs/notes/S08-app.md` (Indonesian): a five-step demo script anyone on the team can follow on presentation day, with the exact sample to click first.
