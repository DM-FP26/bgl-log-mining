# S01. Data acquisition and EDA

## Goal
Download BGL, confirm it is what we think it is, characterise it (including how dirty it is), and produce the EDA figures and tables for the report.

## Depends on
S00.

## Inputs
- Download URL (from Loghub's README): `https://zenodo.org/records/8196385/files/BGL.zip?download=1`
- Expected figures from published papers (use as sanity checks, not as ground truth): **4,747,963 log lines**, **348,460 alert lines (about 7.34%)**.

## Outputs
- `data/raw/BGL.zip`, `data/raw/BGL.log` (not committed). Record file size and SHA-256 in `reports/results.json` → `dataset`.
- `src/bgllog/parsing.py`: `parse_line(raw) -> dict | None` (regex-based field split) and `read_bgl(path, limit=None, offset=0)` yielding rows (chunked).
- `data/interim/parsed.parquet` (fields only; `event_id` is added in S02). Written in chunks.
- `reports/tables/dataset_summary.csv`, `reports/tables/dirty_data_audit.csv`.
- Figures in `reports/figures/` (names in the table below).
- Script: `scripts/s01_download_and_eda.py` (flags: `--sample`, `--force`).
- `tests/test_parsing.py`.

## Steps
1. **Download** with `requests` (stream to disk, show progress). If the download fails or is blocked, stop and write `docs/BLOCKERS.md` (the stop-and-ask rule). Extract the zip.
2. **Inspect the first 20 lines** and write what you see into the stage note. Confirm the field layout in `docs/03-conventions-and-contracts.md` §2. If the real layout differs, fix the regex and update that doc.
3. **Count lines and alerts.** Compare with the expected figures. A difference of more than 1% triggers stop-and-ask.
4. **Parse** every line. Lines that do not match go into a rejects file `data/interim/rejects.txt` (first 1,000 only) and are counted. Never drop silently.
5. **Dirty-data audit** (this is the "najis" evidence; be thorough):

| Check | Output |
|---|---|
| Malformed lines (regex failed) | count and percent |
| Empty or whitespace-only content | count |
| Lines with undecodable bytes (replaced characters) | count |
| Exact duplicate lines | count and ratio |
| Timestamps out of order | count |
| Large time gaps (> 1 hour with no lines) | list of gaps |
| `ts` vs `time_full` disagreement | count |
| Number of distinct alert tags; tags with fewer than 100 lines | table |
| Extremely long messages (> 1,000 characters) | count |
| Missing or unexpected values in `level`, `component`, `type` | table |

6. **EDA figures** (Indonesian titles and labels):

| File | Content |
|---|---|
| `eda_alert_ratio.png` | Alert vs non-alert line counts |
| `eda_alert_tags.png` | Top 20 alert tags (log-scaled y-axis) |
| `eda_lines_per_day.png` | Lines per day, alerts overlaid |
| `eda_alert_bursts.png` | Alert lines per hour (shows burstiness) and the share of alerts inside bursts (`burst_gap_seconds` from config) |
| `eda_level_by_alert.png` | Level distribution split by alert / non-alert |
| `eda_component.png` | Component distribution and alert rate per component |
| `eda_top_nodes.png` | Top 20 nodes by volume and by alert rate |
| `eda_msg_length.png` | Message length distribution (characters) |

7. `dataset_summary.csv`: n_lines, n_alert_lines, alert ratio, time span (first/last timestamp), distinct nodes, distinct components, distinct levels, distinct alert tags, file size.
8. Write numbers into `reports/results.json` (`dataset`, `dirty_data`).
9. `--sample`: process a contiguous slice of `sample.lines` lines starting at `sample.offset` (choose an offset whose slice contains alerts; record it in config).

## Definition of done
- [ ] `data/raw/BGL.log` exists; line count is within 1% of 4,747,963 (or the difference is documented and approved).
- [ ] `parsed.parquet` row count equals the line count (rejects are kept with `parse_ok=False`).
- [ ] Every figure and both tables exist and open correctly.
- [ ] `pytest tests/test_parsing.py` passes (cover at least: a normal alert line, a normal non-alert line, a malformed line, a line with odd bytes).
- [ ] `reports/results.json` has `dataset` and `dirty_data` filled.

## Pitfalls
- Do not `read()` the whole file into memory; iterate and write parquet chunks (for example 200k rows per chunk).
- Use categorical dtype for low-cardinality columns; keep `content` as string.
- BGL contains non-ASCII/garbled bytes: read with `errors="replace"` and count replacements.
- Do not "clean" the data in this stage. S01 only measures. Cleaning decisions belong to S02 and must be documented.

## Report hooks
Chapter IV.1 (EDA) and chapter III.2 (Dataset). Figures: all `eda_*.png`. Tables: `dataset_summary.csv`, `dirty_data_audit.csv`.

## Note to write
`docs/notes/S01-data-and-eda.md` (Indonesian). Must include the three most surprising findings about the data.
