# S02. Preprocessing: templates, windows, split

## Goal
Turn parsed log lines into (1) event IDs via Drain3 templates and (2) fixed-size windows of events with labels and a leakage-safe chronological split. Produce the small `handoff/windows.npz` the GPU teammate will train on.

## Depends on
S01.

## Inputs
`data/interim/parsed.parquet`, `configs/default.yaml` (`parsing.*`, `windows.*`).

## Outputs
- `src/bgllog/parsing.py` (extend): Drain3 wrapper with masking instructions; `assign_event_ids(df_chunks, config) -> event_id column`.
- `src/bgllog/windows.py`: `build_windows(event_ids, is_alert, labels, size, step)`, `chronological_split(n_windows, fractions, gap)`, `build_vocab(train_events, min_count, max_size)`.
- `data/interim/parsed.parquet` updated with `event_id`.
- `data/processed/templates.csv`: `event_id, template, count, alert_line_ratio`.
- `artifacts/drain3_state.bin` (Drain3 `FilePersistence`).
- `artifacts/vocab.json`.
- `data/processed/windows_X.npy` (int16 `[N, W]`) and `data/processed/windows_meta.parquet` (schema in `03-conventions`).
- `handoff/windows.npz` with arrays `X_train`, `X_val`, `X_test` (int16), scalar `vocab_size`, and a JSON string `meta` (window size, step, split sizes, config hash). **No labels in this file.**
- `scripts/s02_preprocess.py`, `tests/test_windows.py`.
- Figures: `prep_template_frequency.png` (rank-frequency of templates, log-log), `prep_templates_per_component.png`, `prep_window_alert_ratio.png`.
- Tables: `reports/tables/preprocessing_summary.csv`.

## Steps
1. **Clean the content string minimally** (do not destroy information): strip whitespace, collapse repeated spaces, drop non-printable characters. Document every transformation in `docs/notes/S02-*.md`.
2. **Drain3 parsing.**
   - Use `drain3.TemplateMiner` with a `TemplateMinerConfig` built in code from `parsing.drain` (defaults: depth 4, sim_th 0.4, max_children 100).
   - Add masking instructions via `MaskingInstruction(regex, mask_with)` for at least: hex (`0x[0-9a-fA-F]+` → `HEX`), IPv4 (→ `IP`), BGL node/location IDs like `R02-M1-N0-C:J12-U11` (→ `NODE`; derive the exact regex from the real data, the example is only a hint), file paths, plain numbers. Drain3 also parametrizes numeric tokens by default.
   - Process in a single streaming pass over `content`. Persist state with `FilePersistence("artifacts/drain3_state.bin")`.
   - After the pass, read the **final** cluster list; map each line's `cluster_id` → `event_id`. Cluster IDs are stable; templates may evolve, so take the final template text for `templates.csv`.
   - **Sanity target:** a few hundred to low thousands of templates. (Loghub-2.0's annotated BGL appears to list 320 templates, which is a useful order-of-magnitude reference.) If you get tens of thousands, the masking is too weak: improve masks or lower `sim_th`/raise depth and re-run. Record every iteration in the note.
3. **Windows.**
   - Default: a single time-ordered stream, window size 20, step 10, `group_by: none`. (Option `group_by: node` is allowed as an ablation; do not make it the default.)
   - Per window: `has_alert`, `n_alert`, `alert_tag` (most frequent alert tag inside, else `NONE`), `ts_start`, `ts_end`.
4. **Chronological split** by window index: 70% train / 15% val / 15% test, with `gap_windows` (default 2) discarded between splits so overlapping windows do not leak across splits. Mark them `split=gap`.
5. **Vocabulary from the train split only.** Reserve 0=PAD, 1=UNK. Events seen fewer than `vocab.min_count` times in train, or not seen in train at all, map to UNK. Cap at `vocab.max_size`.
6. Write `windows_X.npy` using vocab indices; write `windows_meta.parquet`; write `handoff/windows.npz` (compressed). Check its size is below 50 MB; if not, store int16 and reduce nothing else, and stop-and-ask.
7. Report: windows per split, alert-window ratio per split (the splits may differ a lot because alerts are bursty; record it, it matters for S06/S07), UNK ratio per split.
8. Update `reports/results.json` (`dataset.n_templates`, `n_windows`, `split_sizes`, ...).

## Definition of done
- [ ] Every parsed line has an `event_id` (malformed lines get a dedicated `event_id=-1` and are excluded from windows; record how many).
- [ ] Template count is in a sane range (or the deviation is explained in the note).
- [ ] `windows_X.npy` shape is `[N, 20]`; split sizes match 70/15/15 minus gaps (±1 window).
- [ ] **Leakage test passes** (`tests/test_windows.py`): the max line index of train < the min line index of val, same for val < test; vocabulary built only from train.
- [ ] **Label test passes:** hand-built toy stream with known alerts gives the expected `has_alert` / `alert_tag`.
- [ ] `handoff/windows.npz` loads and is below 50 MB.
- [ ] `--sample` mode runs end to end in a short time (the smoke test uses 2,000 lines).

## Pitfalls
- Drain3 is pure Python and processes lines sequentially; for 4.75M lines expect a long single run. Run it once, cache, never re-run without `--force`. Print progress every 100k lines.
- Do not shuffle before windowing. Order matters.
- Do not apply the vocabulary cutoff before the split.
- int16 is enough while the vocabulary is under 32,767.
- Keep `alert_tag` logic deterministic (ties broken by first occurrence).

## Report hooks
Chapter III.3 (Preprocessing pipeline diagram) and IV.2 (Preprocessing results): before/after examples of raw line → masked template → event ID; template frequency plot; window construction illustration (make `prep_window_diagram.png`: a simple schematic with 20 boxes and the 10-step slide).

## Note to write
`docs/notes/S02-preprocessing.md` (Indonesian). Must include one worked example: a raw log line, its template, its event ID, and the window it landed in.
