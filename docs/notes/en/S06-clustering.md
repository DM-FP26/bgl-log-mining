# S06. Clustering

## Execution
1. Used the processed window metadata, S02 split arrays, and S05 LSTM/GRU embeddings. Confirmed the embeddings align with the alert labels and timestamps.
2. Built L2-normalized bag-of-events vectors. Fit TF-IDF, SVD, and deep-embedding scalers on train only; transformed validation and test with those fitted objects.
3. Swept the configured K-Means values. Selected each representation's `k` using validation silhouette on at most 10,000 validation rows; ties prefer smaller `k`. For deep representation selection, the LSTM/GRU validation silhouettes differed by 0.00419, within the 0.01 tolerance, so alert-tag NMI broke the tie: LSTM 0.14086 vs. GRU 0.12885.
4. Evaluated the selected K-Means models on test and repeated each with seeds 42, 43, and 44. Saved each model together with its fitted scaler or TF-IDF/SVD transform in `artifacts/clusters/kmeans_<repr>.joblib`.
5. Fit HDBSCAN on a 100,000-row `has_alert`-stratified train subset after 10-dimensional UMAP reduction. Scikit-learn HDBSCAN has no `predict`, so test assignments use nearest neighbors in the fitted UMAP training space; unprojectable test rows remain noise.
6. Generated the test scatter sample using a 30,000-row `has_alert`-stratified selection, then excluded non-finite UMAP coordinates. The final compressed app artifact contains 29,976 projected rows and is under 100 KB.
7. Wrote the metric and sweep tables, LSTM K-Means test cluster profiles, six figures, and the clustering/sanity sections in `reports/results.json`.

## Results

| Test representation | Selected k | Silhouette | Alert-tag NMI | Alert-window share | Three-seed binary-alert NMI (mean ± SD) | Three-seed binary-alert ARI (mean ± SD) |
|---|---:|---:|---:|---:|---:|---:|
| Bag-of-events | 24 | 0.8294 | 0.0407 | 8.43% | 0.0326 ± 0.0001 | -0.0740 ± 0.0015 |
| TF-IDF+SVD | 24 | 0.8906 | 0.0364 | 8.43% | 0.0328 ± 0.0002 | -0.0771 ± 0.0002 |
| LSTM | 48 | 0.8468 | 0.0959 | 8.43% | 0.0476 ± 0.0082 | -0.0575 ± 0.0173 |
| GRU | 32 | 0.8104 | 0.0787 | 8.43% | 0.0461 ± 0.0110 | -0.0340 ± 0.0024 |

HDBSCAN on LSTM produced 113 train clusters. On test, its silhouette was 0.6788, alert-tag NMI 0.0354, noise ratio 21.46%, and unprojectable ratio 1.44%. The shuffled-label sanity NMI for LSTM was 0.000161 for binary alerts and 0.001898 for alert tags; shuffled values were near zero for all representations.

The test profiles contain 23 occupied clusters although the selected LSTM K-Means model has `k=48`; some fitted clusters receive no test windows. Three interpretable examples:
- Cluster 34: 43,870 windows; 11.08% contain alerts. Common events include debugger termination and correctable memory errors.
- Cluster 30: 9,307 windows; no alerts. Its most frequent event is `iar <*> dear <*>`, an instruction/data address record.
- Cluster 38: 518 windows; all contain alerts, and 512 carry the `KERNTERM` tag. The dominant event reports kernel termination.

## Interpretation and caveats
Silhouette measures separation, not alert relevance: TF-IDF+SVD has the highest test silhouette, while LSTM has the highest alert-tag NMI among K-Means representations. Even LSTM's tag NMI is only 0.0959, and binary-alert ARI is negative. The 92.30% LSTM alert purity is only modestly above the 91.57% non-alert majority baseline, so purity must not be presented alone. Labels were used for validation tie-breaking, stratified sampling, metrics, and shuffled-label sanity checks—not to fit K-Means, scalers, SVD, or UMAP. HDBSCAN noise ratio includes its 1.44% non-finite test projections.

## Reproduction
With the project's Python environment and S02/S05 outputs present:

```powershell
python scripts/s06_cluster.py --sample
python scripts/s06_cluster.py
python -m pytest -q
```

The sample run writes beneath `artifacts/sample/` and `reports/sample/`; the full run writes the committed S06 artifacts and updates `reports/results.json`.

## Issues and resolution
The full log was initially unavailable locally and Zenodo resolution failed. After the user supplied `data/raw/BGL.log`, S02 regenerated the local metadata required for S06. The UMAP scatter omits 24 of the configured 30,000 test points because their coordinates were non-finite; the full-size app artifact is therefore 29,976 points. No validation or test rows were used to fit the clustering pipeline.
