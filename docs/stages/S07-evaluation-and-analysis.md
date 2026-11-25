# S07. Evaluation and analysis

## Goal
Consolidate all results into one source of truth, run the final checks and analysis, and write the limitations honestly. This stage covers the "Uji Coba dan Evaluasi" and "Analisis Hasil" requirements.

## Depends on
S03, S05, S06.

## Outputs
- `scripts/s07_evaluate.py`
- `reports/results.json` (complete, schema-checked against `03-conventions` §5)
- `reports/tables/final_summary.csv` (one-page overview of the main numbers)
- Figures: `eval_overview.png` (one panel summary), `eval_dl_vs_baselines.png`, `eval_loss_alert_vs_normal.png`
- `docs/notes/S07-evaluation-analysis.md` and `docs/limitations.md` (Indonesian)

## Steps

1. **Schema check.** Write `tests/test_results_schema.py` that loads `reports/results.json` and asserts every key from the contract exists and every number is finite. Make S07 fail if it does not pass.
2. **DL evaluation recap (test split only):** loss, perplexity, top-1 and top-5 accuracy for LSTM and GRU vs bigram and most-frequent baselines. State which model was chosen for the app and that the choice used validation metrics.
3. **Anomaly score as a bonus view:** use per-window mean next-event loss from S05. Compute AUROC and average precision of this score for `has_alert` on the test split (and on val for comparison). Plot the loss distribution for alert vs non-alert windows. This shows whether the DL model "knows" what abnormal looks like without ever seeing labels. Interpret with care: alerts are bursty and the split has a different alert rate.
4. **Clustering recap:** pull the test-split table from S06; add the seed spread.
5. **Pattern mining recap:** pull the top rules and the stability result from S03.
6. **Error analysis (write in the note, with numbers):**
   - Which alert tags are best and worst separated by the clusters (from the heatmap)?
   - Which clusters mix alerts and non-alerts the most, and what do their top templates look like?
   - Name three concrete examples (window, cluster, template text) where the clustering "got it right", and two where it clearly did not.
   - Does performance differ between val and test? Why (alert rate, time period)?
7. **Robustness check:** re-run the main K-Means evaluation with window size 10 and 40 on a subsample (not on the full data) to see whether conclusions depend on the window size. Report as a small table (`eval_window_size_sensitivity.csv`). Keep it cheap: reuse the S02 code with a sample and an already trained model only if the vocabulary is unchanged; otherwise use the `bow`/`tfidf_svd` representations only and say so.
8. **Limitations** (`docs/limitations.md`): Drain3 fitted on the whole stream without labels; chronological split with bursty alerts; labels are tags from a 2000s system and may not reflect modern hardware; windows mix nodes in the default stream; no hyperparameter search at scale; a single dataset; embeddings are not guaranteed stable across retrains. Add anything the real results revealed.
9. **Future work** (three bullet points, realistic).

## Definition of done
- [ ] `pytest -q` passes, including the schema test.
- [ ] `reports/results.json` complete; `final_summary.csv` exists.
- [ ] The note contains the error analysis with real numbers and real template examples.
- [ ] `docs/limitations.md` exists and mentions at least the items listed above that apply.
- [ ] All figures regenerate from a single command: `python scripts/s07_evaluate.py --figures` (so the team can reproduce them).

## Pitfalls
- Do not cherry-pick: report the table you have, including unflattering rows.
- Do not use the test split for any choice.
- Keep claims proportional to evidence: "clusters are associated with alert tags" is fine; "the model predicts failures" is not.

## Report hooks
Chapter IV.6 (Evaluasi) and IV.7 (Analisis hasil), chapter V (Kesimpulan) built from `limitations.md` and the future work bullets.

## Note to write
`docs/notes/S07-evaluation-analysis.md` (Indonesian): the three most important findings, one limitation each teammate must be able to state, and a one-sentence honest conclusion.
