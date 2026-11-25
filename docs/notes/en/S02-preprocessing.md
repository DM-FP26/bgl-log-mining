# S02. Preprocessing: templates, windows, split (technical log, English)

Indonesian summary for presentation: `docs/notes/S02-preprocessing.md`. Numbers come from `reports/results.json` (`preprocessing`), `reports/tables/preprocessing_summary.csv` and `data/processed/templates.csv`.

## Goal
Turn parsed lines into event ids (Drain3), fixed windows with labels, a leakage-safe chronological split, a train-only vocabulary, and the label-free `handoff/windows.npz` for the GPU teammate.

## Steps taken (in order)
1. **Minimal cleaning** (`clean_content` in `src/bgllog/parsing.py`): drop control and U+FFFD characters, collapse whitespace, strip. An empty result becomes the token `<EMPTY>` (34,474 lines changed: the 34,470 empty messages plus 4 others).
2. **Masks** in `configs/default.yaml` (applied in order, Drain3 `MaskingInstruction`): `HEX` (`0x...`), `IP` (with optional `:port`), `NODE` (`R\d\d-M\d...`), `HEXW` (bare hex words of 6+ chars containing a letter), `PATH`, `NUM` (`\b\d+\b`).
3. **Drain3** built in code from `parsing.drain` (depth 4, sim_th 0.4, max_children 100), no ini file. **Speed trick:** only the 358,360 *unique* cleaned messages are fed to Drain3, in first-appearance order, then mapped back to all lines (`assign_event_ids`). Identical messages cannot create new templates, so clusters are equivalent to a full pass; the run takes about 20 seconds instead of minutes. State is saved once at the end (`artifacts/drain3_state.bin`, 20 KB); Drain3's per-change snapshotting would be very slow.
4. **Iteration log for masks** (target: hundreds to low thousands of templates):
   | Masks | Templates | Singletons |
   |---|---|---|
   | HEX, IP, NODE, PATH, NUM | 1,126 | 630 (register dumps with bare hex such as `1416a3f8`) |
   | + HEXW | 396 | 21 |
   I kept the second. 102 templates cover 99% of lines. Reference point: Loghub-2.0's BGL annotation lists about 320.
5. **Event ids** written back into `data/interim/parsed.parquet` (`event_id`, int32, atomic replace); malformed lines would get -1 (there are none). `data/processed/templates.csv` has `event_id, template, count, alert_line_ratio`.
6. **Windows** (`src/bgllog/windows.py`): one time-ordered stream, size 20, step 10, so `N = (4,747,963 - 20) // 10 + 1 = 474,795`. Per window: `n_alert`, `has_alert`, `alert_tag` (most frequent tag, ties broken by first occurrence).
7. **Split** by window index: 70/15/15 with a 2-window gap. With step 10 and size 20, windows i and i+2 do not share lines, so no line is shared across splits. Result: train 332,356, val 71,219, test 71,216, gap 4.
8. **Vocabulary from train lines only** (lines covered by train windows), `min_count` 5, `max_size` 2000; 0=PAD, 1=UNK, most frequent first, ties by event id. Size 241. Events below the cutoff or unseen in train become UNK.
9. **Outputs:** `data/processed/windows_X.npy` (int16, 474,795 x 20), `windows_meta.parquet`, `artifacts/vocab.json`, `handoff/windows.npz` (0.3 MB, no labels: `X_train`, `X_val`, `X_test`, `vocab_size`, `meta` JSON with config hash), figures `prep_template_frequency`, `prep_templates_per_component`, `prep_window_alert_ratio`, `prep_unk_ratio`, `prep_window_diagram`, table `preprocessing_summary.csv`, and `results.json` (`dataset.*`, `preprocessing`).
10. **Tests** (`tests/test_windows.py`, 35 tests total pass): window shapes, hand-built toy label stream (alerts at known lines give expected `has_alert`, `n_alert`, `alert_tag`), tie-break, split leakage (train max line < val min line < test min line), train-only vocabulary with UNK mapping, vocab size cap, cleaning, and a 2,000-line synthetic end-to-end smoke test.

## Findings
- 396 templates; window alert ratio: train 9.00%, val 6.47%, test 8.43% (much more even than feared after S01).
- **Concept drift in the test split.** Test UNK token ratio is 60.5% (train 0.002%, val 2.2%); 64.4% of test windows contain at least one UNK, 60.2% are majority UNK. Cause: events that never occur before the test period, mostly two one-off machine-wide counter dumps on 1 to 4 Dec 2005 (135,092 lines each from 65,533 nodes), plus `ciod: Received signal ...` (39,457), `ciod: Error reading message prefix on CioStream socket ...` (28,802, 100% alert), a kernel integer-alignment message (22,175) and a single-node `MACHINE CHECK` burst (14,482). Only 25,356 test windows are UNK-free, and only 1,056 of those contain an alert.

## Decision needed for S05 to S07 (not blocking S03/S04)
The spec split is kept (it is the honest, standard choice). Recommendation: report every test metric twice, on all test windows and on the UNK-free subset, and say so in the report. Alternatives, if the UNK-free subset proves too small for NMI/ARI: (a) also evaluate on val (only 2.6% of windows have UNK) or (b) use blocked time folds. Both weaken the "simple chronological split" story, so decide after seeing S06 results.

## Caveats
- The vocabulary cutoff (`min_count` 5) is measured over train tokens, where long runs of identical events inflate counts. Events frequent only in a short burst still enter the vocabulary.
- Window labels ignore *which* node produced a line: the stream is global, so a window can mix lines from many nodes (`group_by: node` is the ablation).
- `windows.npz` is tiny (0.3 MB) because the data is extremely repetitive; compression is not a sign of a problem.

## Problems hit
| Problem | Fix |
|---|---|
| 630 singleton templates after first masks | Added `HEXW` mask |
| Title of `prep_unk_ratio.png` cut off | Shortened |
| Sample outputs showed up in `git status` | `data/processed/*_sample*` ignored |

## Reproduce
```bash
.venv/bin/python scripts/s02_preprocess.py --sample   # fast, separate outputs
.venv/bin/python scripts/s02_preprocess.py            # full, cached; --force recomputes Drain3
.venv/bin/python -m pytest -q
```
