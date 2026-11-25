# S03. Pattern mining

## Goal
Find event combinations and event sequences that are characteristic of the windows right before alerts, using classic data-mining algorithms (FP-Growth, association rules, PrefixSpan).

## Depends on
S02. May run while the GPU teammate is training (S05).

## Inputs
`data/interim/parsed.parquet`, `data/processed/windows_meta.parquet`, `data/processed/windows_X.npy`, `data/processed/templates.csv`, `configs/default.yaml` (`patterns.*`).

## Outputs
- `src/bgllog/patterns.py`
- `scripts/s03_patterns.py`
- Tables: `reports/tables/frequent_itemsets.csv`, `association_rules.csv`, `sequential_patterns_prealert.csv`, `pattern_examples.csv` (3–5 readable examples with templates spelled out).
- App copies: `artifacts/patterns/rules.csv`, `artifacts/patterns/seq_patterns.csv` (top 200 each, with template text).
- Figures: `pat_top_rules_lift.png`, `pat_support_confidence.png`, `pat_top_seq_patterns.png`.
- `reports/results.json` → `patterns`.

## Definitions (use exactly these)

- **Burst:** consecutive alert lines whose gaps are ≤ `patterns.burst_gap_seconds` (default 300). The **first alert line of a burst** is the burst start.
- **Pre-alert window (P):** the `windows.size` event lines immediately **before** a burst start (so the window contains no line from the burst itself). Build these directly from the line stream, not from the sliding windows.
- **Control window (C):** a window of the same size drawn from time ranges that are at least `patterns.control_margin_minutes` (default 60) away from any alert line, sampled uniformly. Draw as many as P (cap both at `patterns.max_windows_per_class`, default 20,000).
- Pre-alert windows should be **tagged** with the alert tag of the burst start, so patterns can be reported per tag later.

## Steps
1. Build P and C. Report counts, and the number of bursts found. Check that P and C do not overlap with each other.
2. **Itemsets:** each window → a set of event IDs (items). Use the vocabulary of the top `patterns.max_items` events (default 150) so the one-hot matrix stays small (use a sparse boolean DataFrame). Run `mlxtend.frequent_patterns.fpgrowth(min_support=patterns.min_support)` on P ∪ C (default min_support 0.02), `use_colnames=True`.
3. **Association rules with consequent = PRE_ALERT:** add a column item `PRE_ALERT` (True for P, False for C). Generate rules with `association_rules` (metric `lift`, min threshold `patterns.min_lift`, default 1.2), then keep only rules whose consequent is exactly `{PRE_ALERT}` and whose confidence ≥ `patterns.min_confidence` (default 0.6). Report support, confidence, lift, leverage and the template text for each antecedent item.
4. **Sequential patterns:** run `prefixspan.PrefixSpan` separately on sequences from P and from C (sample at most `patterns.seq_sample` windows each, default 10,000; use closed patterns if available, limit pattern length via `minlen/maxlen` if the library supports it, otherwise filter after). Compute support in P and in C; keep patterns with support_P ≥ `patterns.seq_min_support` and `support_P / max(support_C, epsilon) ≥ patterns.seq_min_ratio` (default 2.0).
5. **Make it human-readable:** join event IDs to template text; shorten long templates in figures but keep full text in CSV.
6. **Honest checks (write results to the note):**
   - Do the top rules just contain templates that are themselves fatal-looking error messages? Say so; these are still useful but less surprising.
   - Re-run the rule mining with a different random control sample (seed 43) and report how many of the top 20 rules survive. This is the stability check.
7. Write `results.json.patterns`: n_itemsets, n_rules, top 10 rules, top 10 sequential patterns, stability result.

## Definition of done
- [ ] P and C built with the stated definitions; counts reported; no overlap.
- [ ] At least one rule table and one sequential-pattern table exist and are non-empty. If they are empty at the default thresholds, lower thresholds step by step and document each step (do not fabricate).
- [ ] Every rule row has human-readable template text.
- [ ] Stability check done (seed 42 vs 43).
- [ ] App copies exist in `artifacts/patterns/`.

## Pitfalls
- One-hot of all events × hundreds of thousands of windows will blow memory. Use the top-N vocabulary, a sparse frame, and the P/C balanced sample.
- Do not mine rules on windows that include the alert lines themselves; that is trivially circular.
- PrefixSpan is slow in pure Python: respect `seq_sample`.
- `min_support` must be relative to P ∪ C, which is balanced; say that in the report.

## Report hooks
Chapter IV.3 (Pattern mining). Figures: `pat_*.png`. Tables: `association_rules.csv` (top 10), `sequential_patterns_prealert.csv` (top 10), `pattern_examples.csv`. Theory in chapter II: support, confidence, lift, FP-Growth, PrefixSpan.

## Note to write
`docs/notes/S03-pattern-mining.md` (Indonesian). Include the plain-language meaning of support, confidence and lift, with one real example from the results.
