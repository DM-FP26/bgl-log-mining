# S03. Pattern mining (technical log, English)

Indonesian summary: `docs/notes/S03-pattern-mining.md`. Numbers come from `reports/results.json` (`patterns`) and `reports/tables/`.

## Goal
Find event combinations and sequences that characterise the 20 lines right before an alert burst, versus quiet periods (FP-Growth, association rules, PrefixSpan).

## Steps taken (in order)
1. **Burst starts** (`find_burst_starts` in `src/bgllog/patterns.py`): alert lines at most 300 s apart form a burst; the first alert line is the start. 820 bursts.
2. **Pre-alert windows P** (`build_prealert`): the 20 stream lines immediately before each burst start. Windows that contain any alert line (from an earlier burst) are dropped: 214 of 820, leaving **606** (0 dropped for lack of room). Each P window carries the alert tag of its burst start.
3. **Control windows C** (`control_candidates`, `build_control`): grid-aligned 20-line blocks whose every line is at least 60 minutes from every alert line, with blocks touching a P window removed; sample as many as P (606) uniformly, seed 42. Grid alignment guarantees controls never overlap each other; the script asserts zero P/C overlap.
4. **Items:** the top 150 events by document frequency in P and C; one boolean column per event plus `PRE_ALERT` (True for P). 
5. **FP-Growth** (`mlxtend` 0.25) with `min_support` 0.02 (relative to the balanced P+C set), `max_len` 4 (added to keep rules readable): 196 itemsets. **Rules** via `association_rules(metric="lift", min_threshold=1.2)`, then only rules with consequent exactly `{PRE_ALERT}` and confidence at least 0.6: **83 rules**. No threshold lowering was needed (`checks.threshold_steps_rules` has one step).
6. **PrefixSpan** on pre-alert sequences (consecutive duplicates collapsed, closed patterns, length 2 to 5, min support 0.05). Support in C is computed by direct subsequence counting on the control sequences (more exact than mining C separately, which would miss patterns under its own support threshold). Kept patterns with support_P at least 0.05 and ratio at least 2.0 (ratio uses epsilon 1e-3): **293 patterns**.
7. **Outputs:** `frequent_itemsets.csv`, `association_rules.csv`, `sequential_patterns_prealert.csv`, `pattern_examples.csv`, `artifacts/patterns/{rules,seq_patterns}.csv` (top 200 each, with template text), figures `pat_top_rules_lift.png` (despite its name it plots coverage, see below), `pat_support_confidence.png`, `pat_top_seq_patterns.png`.
8. **Honest checks** (all in `results.json` under `patterns.checks`):
   - *Obvious fatal messages?* 10% of the top-20 rules have an error-level majority antecedent; 0% contain alert-labelled events.
   - *Stability (control seed 43):* 16 of the top-20 rules are again in the top 20, 20 of 20 found anywhere among the 83 re-mined rules.
   - *Time-matched control:* P and C balanced month by month; top-20 median lift 2.0, 20 of 20 re-found when mining afresh. Rules out the time confound I suspected after seeing that uniform controls came 61% from June and July.
   - *Temporal hold-out:* mine on the first 70% (by time) of windows, evaluate the top 20 on the last 30% (206 P, 158 C): median lift 1.77; 60% of the rules keep lift at least 1.2.
9. **Tests** (`tests/test_patterns.py`, 5 tests): burst gap logic, no alert lines in P, no P/C overlap and margin respected, rules recover a planted perfect predictor (confidence 1.0, lift 2.0), subsequence logic. 48 tests in total pass.

## Findings
- Top rules are all about memory error correction (`ddr errors detected and corrected`, `CE sym`, `MidplaneSwitchController ... bit sparing`, `ddr: activating redundant bit steering`). 247 of the 606 pre-alert windows precede a `KERNMC` (machine check) burst, so the patterns mostly describe precursors of machine checks.
- Best rule: bit sparing + ddr errors detected and corrected: support 0.042, confidence 1.0, lift 2.0 (maximum possible because P and C are balanced, so lift = confidence / 0.5). It covers 8.4% of pre-alert windows: high precision, low recall.
- Best sequence: a run of ddr corrected-error messages interleaved with `CE sym`, in 11.4% of P windows and 0% of C.

## Caveats (important for the report)
- **Low recall.** The best single-event rule covers about 12% of P windows; no rule predicts most alert bursts.
- **Contrast is "near an alert episode" vs "quiet".** Controls are at least 60 minutes from any alert, so a pattern that appears only in P could mean "an episode has already begun", not a long-range precursor. Many P windows are close to earlier activity (the 214 dropped ones show how dense episodes are).
- **Global stream.** The 20 lines come from all nodes interleaved in time; a pattern's events may come from different nodes than the alert. A per-node variant (`windows.group_by: node`) is the natural ablation.
- **Interpretation of the physical mechanism** (memory errors escalating to machine checks) is my reading of domain terms, not something tested here.
- The sequential ratio is capped by epsilon (support_C = 0 gives ratio support_P / 0.001); read it as "never in control".

## Problems hit and how they were fixed
| Problem | Fix |
|---|---|
| 214 of 820 P windows contain earlier alert lines | Dropped (documented); otherwise mining would be circular |
| Uniform controls came 61% from Jun/Jul while P spans all months | Added the time-matched control check |
| `pat_top_rules_lift.png` was useless (every lift capped at 2.0), labels truncated identically | Plot coverage (% of P windows) with confidence as annotation; readable event nicknames, wrapped labels (file name kept for the contract) |

## Reproduce
```bash
.venv/bin/python scripts/s03_patterns.py --sample   # plumbing check, outputs in reports/sample/
.venv/bin/python scripts/s03_patterns.py            # full, about 10 seconds
.venv/bin/python -m pytest -q
```
