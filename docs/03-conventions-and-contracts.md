# 03. Conventions and contracts

Stages talk to each other through files. These are the contracts. Do not rename them without updating every spec.

## 1. Paths

| Path | Content | Committed? |
|---|---|---|
| `data/raw/BGL.zip`, `data/raw/BGL.log` | Original download | No |
| `data/interim/parsed.parquet` | One row per log line (schema below) | No |
| `data/processed/templates.csv` | `event_id, template, count, alert_line_ratio` | Yes (small) |
| `data/processed/windows_X.npy` | int16 array `[N_windows, W]` of vocab IDs (0=PAD, 1=UNK) | No |
| `data/processed/windows_meta.parquet` | One row per window (schema below) | No |
| `artifacts/vocab.json` | event_id → vocab index, built on the train split | Yes |
| `artifacts/drain3_state.bin` | Drain3 persisted state (for the app) | Yes if < 20 MB |
| `artifacts/models/<lstm\|gru>/best.pt`, `config.json`, `history.csv`, `metrics.json` | Trained model + curves | Yes (small) |
| `artifacts/embeddings/<lstm\|gru>_<split>.npy` | Window embeddings (float32) | No |
| `artifacts/clusters/` | `kmeans_<repr>.joblib`, `cluster_profiles.json`, `umap_sample.npz` | Yes (small only) |
| `artifacts/patterns/rules.csv`, `seq_patterns.csv` | Mined patterns for the app | Yes |
| `artifacts/demo_samples.json` | Raw-line demo windows for the app | Yes |
| `handoff/windows.npz` | `X_train, X_val, X_test, vocab_size, meta` for GPU training (no labels) | Yes (must stay < 50 MB) |
| `handoff/results/` | Filled by the GPU teammate | Yes |
| `reports/figures/*.png` | Figures at 200 dpi | Yes |
| `reports/tables/*.csv` | Tables | Yes |
| `reports/results.json` | **Single source of truth for every number** | Yes |

Size guard: never commit a single file larger than 50 MB.

## 2. `parsed.parquet` schema

| Column | Type | Meaning |
|---|---|---|
| `line_id` | int32 | 0-based line number in `BGL.log` |
| `label` | category | First column; `-` = non-alert, anything else = alert tag |
| `is_alert` | bool | `label != "-"` |
| `ts` | int64 | Unix timestamp (second column) |
| `date` | string | `YYYY.MM.DD` |
| `node` | category | Node/location ID (fourth column) |
| `time_full` | string | Full timestamp with microseconds |
| `type` | category | e.g. RAS |
| `component` | category | e.g. KERNEL, APP, MMCS (verify on real data) |
| `level` | category | e.g. INFO, WARNING, ERROR, FATAL, SEVERE, FAILURE (verify) |
| `content` | string | Raw message text |
| `parse_ok` | bool | False when the line did not match the expected format |
| `event_id` | int32 | Drain3 cluster id (added in S02) |

Expected raw line layout (verify empirically in S01):

```
<Label> <Timestamp> <Date> <Node> <Time> <NodeRepeat> <Type> <Component> <Level> <Content...>
- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.675872 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction cache parity error corrected
```

## 3. `windows_meta.parquet` schema

| Column | Meaning |
|---|---|
| `window_id` | 0..N-1, in time order |
| `start_line`, `end_line` | Line range in `BGL.log` |
| `ts_start`, `ts_end` | Unix seconds |
| `has_alert` | Any alert line inside the window |
| `n_alert` | Number of alert lines inside |
| `alert_tag` | Most frequent alert tag inside the window, or `NONE` |
| `split` | `train` / `val` / `test` / `gap` |

## 4. Config

`configs/default.yaml` holds all knobs (see `starter/configs/default.yaml`). Scripts take `--config` (default `configs/default.yaml`), `--sample`, `--force`. Never hard-code a path or a hyperparameter in code.

## 5. `reports/results.json` contract

Top-level keys (add, never rename):

```
dataset:    {n_lines, n_alert_lines, alert_line_ratio, n_templates, n_windows, n_windows_with_alert, window_size, window_step, split_sizes}
dirty_data: {malformed_lines, empty_content, non_utf8_lines, duplicate_line_ratio, timestamp_out_of_order, ...}
dl:         {lstm: {...metrics}, gru: {...metrics}, baselines: {bigram_top1, most_frequent_top1}}
clustering: [ {representation, algorithm, k, silhouette, davies_bouldin, calinski_harabasz, nmi_alert_tag, ari_alert_tag, homogeneity, completeness, split} ... ]
patterns:   {n_itemsets, n_rules, top_rules: [...], top_seq_patterns: [...]}
sanity:     {shuffled_label_nmi, chance_baselines, seeds_checked, ...}
env:        {python, torch, cuda, gpu_name, platform}
```

## 6. Code and style

- Package `src/bgllog`, importable via `pip install -e .` (add a minimal `pyproject.toml` in S00).
- Type hints on public functions; short docstrings; no notebooks required (a notebook for the EDA is optional and must not be the only source of a figure).
- Logging with the `logging` module, INFO to console and `logs/<stage>.log`.
- Figures: matplotlib/seaborn, one consistent style, 200 dpi, titles and axis labels in **Indonesian** (they go into the report), file names in English (`eda_alert_ratio.png`).
- Tables: CSV with English column names; the report translates headers.

## 7. Git

- Default branch `main`. One commit per finished stage: `Sxx: short description`.
- GPU teammate pushes only to `gpu-run`. Claude Code merges it with `git merge --no-ff origin/gpu-run` after validating (S05).
- No force pushes. No rewriting history.
