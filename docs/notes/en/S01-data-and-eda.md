# S01. Data acquisition and EDA (technical log, English)

Indonesian summary for presentation: `docs/notes/S01-data-and-eda.md`. All numbers below come from `reports/results.json` and `reports/tables/*.csv`; re-read those files, do not trust this text if they differ.

## Goal
Download BGL, characterise it, audit how dirty it is, produce EDA tables and figures. S01 only measures; it does not clean.

## Steps taken (in order)
1. **Download and extract.** `https://zenodo.org/records/8196385/files/BGL.zip?download=1` (57 MB zip, 743 MB `BGL.log`) into `data/raw/` (git-ignored). First done by hand with `curl` during planning; the script now does it with `requests` and skips it when `BGL.log` exists. SHA-256 of both files is stored in `results.json` under `dataset`.
2. **Manual inspection** of `head`, random lines and `awk` field counts. This revealed the real layout:
   `label ts date node time_full [node_repeat] type component level [content]`. Two quirks the spec did not anticipate: the node-repeat field is sometimes absent (324 lines), and the message can be empty (34,470 lines).
3. **Parser** (`src/bgllog/parsing.py`): `parse_line(raw)` splits the first 5 fields, validates `ts`/`date`/`time_full` with regexes, decides whether the node-repeat field is present by checking whether the next token equals `node`, then splits type/component/level/content. Returns `None` for malformed lines. `read_bgl(path, limit, offset)` streams the file as UTF-8 with `errors="replace"` and never loads it whole.
4. **Streaming parse and audit** (`parse_and_audit` in `scripts/s01_download_and_eda.py`): one pass over all lines, written to `data/interim/parsed.parquet` in chunks of 200k rows (zstd, explicit pyarrow schema, so every row is kept, malformed ones with `parse_ok=False`). Counters collected in the same pass: malformed, empty content, replacement-character lines, non-ASCII lines, long messages (>1000 chars), exact duplicates (set of line hashes), out-of-order timestamps, gaps over 1 hour, missing node-repeat, and `ts` vs `time_full` offset.
5. **Time consistency check.** `ts` is Unix UTC; `time_full` is local lab time. We compute `ts - timegm(time_full)` per line; the expected values are 25200 s (PDT) or 28800 s (PST). Every line matched (0 disagreements).
6. **EDA and tables** (`run_eda`): reads only the needed columns back from parquet; writes `dataset_summary.csv`, `dirty_data_audit.csv`, `alert_tags.csv`, `field_values.csv`, `time_gaps.csv`; computes alert bursts (consecutive alert lines at most `eda.burst_gap_seconds`=300 s apart form one burst).
7. **Figures** (8 PNGs, 200 dpi, Indonesian titles): `eda_alert_ratio`, `eda_alert_tags`, `eda_lines_per_day`, `eda_alert_bursts`, `eda_level_by_alert`, `eda_component`, `eda_top_nodes`, `eda_msg_length`.
8. **Sanity gate.** Line and alert counts are compared with 4,747,963 / 348,460 (tolerance 1%); the script exits with code 3 if off. Actual: exact match.
9. **Tests:** `tests/test_parsing.py` (normal line, alert line, missing node-repeat, empty content, malformed line, odd bytes, offset/limit). Total 27 tests pass.
10. **Sample mode.** `--sample` processes `sample.lines` (200,000) from `sample.offset`. I counted alerts per 200k slice with `awk` and chose offset 3,000,000 (about 10% alerts, close to the real 7.3%). Sample outputs go to `data/interim/*_sample*` and `reports/sample/` and never touch `results.json`.

## Findings (see the tables for exact numbers)
- Structure is clean: 0 malformed, 0 out-of-order, 0 time-field disagreements.
- Content is messy: 34,470 empty messages, 116,659 lines with node `-`/`NULL`/`UNKNOWN_LOCATION`, 8 corrupted lines (junk in `type`/`component`/`level`, visible in `field_values.csv`), 1,005 gaps over an hour, 4 duplicate lines.
- `level == FATAL` is not the alert label: 507,103 of 855,501 FATAL lines are not alerts.
- Alerts are extremely bursty: 820 bursts, 99.6% of alerts in bursts of at least 10 lines, largest burst 152,183 lines; one node (`R30-M0-N9-C:J16-U01`) holds 43.7% of alerts and June 2005 holds 64.6%.

## Problems hit and how they were fixed
| Problem | Fix |
|---|---|
| My first `awk` profile mislabelled columns (lines with a missing node field shift fields), so early numbers (306 missing-node lines; 506,260 non-alert FATAL) were off | Replaced by the real parser; docs corrected |
| `--force` re-downloaded the 57 MB zip | Download no longer depends on `--force`; it only recomputes parsing and EDA |
| `eda_alert_bursts.png`: log axis hid most hours | `vlines` from 0.5 with explicit y-limits |
| `eda_level_by_alert.png`: junk levels (`0`, `a`, `iar`, `KERNEL`) from corrupted lines | Levels with fewer than 100 lines are dropped from the plot only (tables keep them) |
| `eda_top_nodes.png`: overlapping x tick labels | Plain number format, rotated |
| Audit missed `UNKNOWN_LOCATION` as a missing-node value | Added to the node check (89,620 became 116,659) |

## Caveats
- Duplicate detection uses Python `hash()` of each line (collision chance negligible at 4.7M lines, but not literally zero).
- "Bursts" are chain-based with a 300 s gap, so one very long storm can chain into a single enormous burst (152,183 lines). Report both the burst count and the share, not the maximum alone.
- Epoch-offset check assumes only PDT/PST. A different offset would be counted as a disagreement.

## Reproduce
```bash
.venv/bin/python scripts/s01_download_and_eda.py --sample   # about 10 seconds, outputs in reports/sample/
.venv/bin/python scripts/s01_download_and_eda.py            # full, idempotent; --force recomputes
.venv/bin/python -m pytest -q
```
Outputs: `data/interim/parsed.parquet` (not committed), `reports/tables/*.csv`, `reports/figures/eda_*.png`, `reports/results.json` (`dataset`, `dirty_data`).
