# S06. Clustering

## Goal
Cluster window embeddings, compare against non-deep baselines, and describe what each cluster means.

## Depends on
S05 (embeddings for train/val/test).

## Representations to compare (all computed on the same windows)

| Name | How |
|---|---|
| `bow` | Bag-of-events: count vector over the vocabulary, L2-normalised |
| `tfidf_svd` | TF-IDF over event counts (fit on train), then `TruncatedSVD` to `clustering.svd_dims` (default 64) fit on train |
| `lstm` | Mean-pooled hidden-state embeddings from S05 |
| `gru` | Same, GRU |

Optional ablation (only if cheap): `lstm_last` using last-state pooling.

## Algorithms

1. **MiniBatchKMeans** (primary; scalable; has `predict`). Sweep `k` over `clustering.k_values` (default 4, 6, 8, 12, 16, 24, 32, 48), `n_init` ≥ 5, seed 42. Standardise embeddings (fit on train) before clustering for `lstm`/`gru`.
2. **HDBSCAN** (secondary, exploratory): scikit-learn's `HDBSCAN` has no `predict` for new points in the versions we checked (confirm with `hasattr`); if that holds, use this protocol:
   - Reduce a stratified **subsample of train** (default 100,000 windows) with UMAP to `clustering.umap_dims` (default 10) dims for clustering (`n_neighbors=30`, `min_dist=0.0`, `metric=euclidean`, seed 42).
   - Fit HDBSCAN on that subsample (`min_cluster_size` from config, default 200).
   - Assign every other window (val/test, and rest of train) to the label of its **nearest neighbour** in the fitted subsample (use `sklearn.neighbors.NearestNeighbors` on the UMAP space via `umap.transform`). Points whose nearest clustered neighbour is noise stay noise.
   - Report the noise ratio. HDBSCAN is not used in the app; it is a finding.

## Protocol (leakage-safe)

- **Fit** every scaler, SVD, UMAP and clustering model on the **train** split only.
- **Choose k** per representation using **validation** windows: maximise silhouette (computed on a random sample of at most 10,000 windows, because silhouette is O(n²)) and check Davies–Bouldin. Break ties with the smaller k. Record the choice and the sweep table.
- **Report on test** windows with the chosen k.
- **Seeds:** repeat K-Means with 3 seeds (42, 43, 44); report mean ± std of NMI and ARI.

## Metrics

Internal (no labels): silhouette (sampled), Davies–Bouldin, Calinski–Harabasz.
External (against the labels S02 stored): NMI, ARI, homogeneity, completeness, for **two** labelings: `has_alert` (binary) and `alert_tag` (multiclass, `NONE` for no-alert windows). Also **cluster purity** w.r.t. `has_alert`.
Sanity: NMI against a **shuffled** copy of the labels (should be near 0) to show the real NMI is not chance. Store in `results.json.sanity`.

## Cluster profiles (for the report and the app)

For the chosen K-Means model of the **best representation** (best = highest validation silhouette among `lstm` and `gru`; if they are within 0.01, prefer the one with the higher validation NMI on `alert_tag`) compute per cluster:
size and share, alert-window rate, distribution of alert tags (top 3), top 10 events by frequency and by lift vs the global distribution (with template text), the mean position in time (do clusters correspond to periods?), and **one representative window** (closest to the centroid) printed as readable template lines.
Save as `artifacts/clusters/cluster_profiles.json` and `reports/tables/cluster_profiles.csv`.

## Outputs
- `src/bgllog/clustering.py`, `scripts/s06_cluster.py`, `tests/test_clustering.py` (tiny synthetic blobs recover obvious clusters).
- `artifacts/clusters/kmeans_<repr>.joblib` for the app-relevant representation(s) (small), plus the scaler.
- `artifacts/clusters/cluster_profiles.json`.
- `artifacts/clusters/umap_sample.npz`: a 30,000-point stratified sample of test windows with 2-D UMAP coordinates, cluster id, `has_alert`, `alert_tag` (for the app scatter plot; if it is above 20 MB reduce the sample).
- Tables: `reports/tables/clustering_metrics.csv` (all rows of the contract in `03-conventions`), `clustering_k_sweep.csv`, `cluster_profiles.csv`.
- Figures: `clu_k_sweep.png` (silhouette and DB vs k per representation), `clu_umap_clusters.png`, `clu_umap_alerts.png` (same 2-D map coloured by alert), `clu_cluster_alert_rate.png`, `clu_confusion_tag_vs_cluster.png` (heatmap of alert tag × cluster, normalised), `clu_representation_comparison.png`.
- `reports/results.json` → `clustering`, `sanity`.

## Definition of done
- [ ] Metrics table has every representation × {KMeans chosen k} (test split) and the HDBSCAN row for the best representation.
- [ ] The three-seed mean ± std is reported.
- [ ] Shuffled-label sanity result stored and in the note.
- [ ] Cluster profiles exist with template text; at least three clusters are described in plain language in the note.
- [ ] No model was fit on val/test (code review: grep that `fit` calls only receive train arrays).
- [ ] The app artifacts exist and are small.

## Pitfalls
- Do not compute full silhouette on hundreds of thousands of points.
- Do not choose k with test data.
- The alert-window share can differ strongly between splits because alerts are bursty: always show it next to external metrics.
- UMAP is stochastic and slow the first time; fix the seed, keep subsamples, cache the fitted reducer (do not commit if large).
- If deep embeddings do **not** beat the baselines, report that clearly. Do not tune until they do.

## Report hooks
Chapter IV.5 (Clustering results and analysis). Chapter II: K-Means, HDBSCAN, silhouette, Davies–Bouldin, NMI, ARI, UMAP.

## Note to write
`docs/notes/S06-clustering.md` (Indonesian): what a cluster is here, how we know it is meaningful, and the finding on LSTM vs GRU vs baselines.
