"""Leakage-safe clustering helpers for S06."""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score, completeness_score,
                             davies_bouldin_score, homogeneity_score, normalized_mutual_info_score,
                             silhouette_score)
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import normalize


def event_count_matrix(windows: np.ndarray, vocab_size: int) -> csr_matrix:
    """Build L2-normalized sparse event-count vectors, ignoring PAD and UNK."""
    rows = np.repeat(np.arange(len(windows)), windows.shape[1])
    cols = windows.reshape(-1)
    keep = cols > 1
    counts = csr_matrix((np.ones(int(keep.sum()), dtype=np.float32), (rows[keep], cols[keep])),
                        shape=(len(windows), vocab_size), dtype=np.float32)
    return normalize(counts, norm="l2", axis=1, copy=False)


def fit_kmeans(features: Any, k: int, seed: int, batch_size: int = 8192) -> MiniBatchKMeans:
    """Fit scalable K-Means on the supplied training features only."""
    model = MiniBatchKMeans(n_clusters=k, random_state=seed, n_init=5, batch_size=batch_size,
                            max_iter=100, reassignment_ratio=0.01)
    model.fit(features)
    return model


def external_metrics(clusters: np.ndarray, has_alert: np.ndarray, alert_tag: np.ndarray) -> dict[str, float]:
    """Return external scores and binary-alert purity for one partition."""
    tags = np.asarray(alert_tag).astype(str)
    alert = np.asarray(has_alert, dtype=bool)
    cluster = np.asarray(clusters)
    purity = 0.0
    total = len(cluster)
    for label in np.unique(cluster):
        in_cluster = alert[cluster == label]
        if in_cluster.size:
            purity += max(int(in_cluster.sum()), int((~in_cluster).sum()))
    return {
        "nmi_alert": float(normalized_mutual_info_score(alert, cluster)),
        "ari_alert": float(adjusted_rand_score(alert, cluster)),
        "homogeneity_alert": float(homogeneity_score(alert, cluster)),
        "completeness_alert": float(completeness_score(alert, cluster)),
        "purity_alert": purity / total if total else float("nan"),
        "nmi_alert_tag": float(normalized_mutual_info_score(tags, cluster)),
        "ari_alert_tag": float(adjusted_rand_score(tags, cluster)),
        "homogeneity_alert_tag": float(homogeneity_score(tags, cluster)),
        "completeness_alert_tag": float(completeness_score(tags, cluster)),
    }


def internal_metrics(features: Any, clusters: np.ndarray, sample_size: int, seed: int) -> dict[str, float]:
    """Compute internal scores on a deterministic sample to bound runtime."""
    labels = np.asarray(clusters)
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(labels), min(len(labels), sample_size), replace=False)
    sampled_labels = labels[indices]
    if len(np.unique(sampled_labels)) < 2 or len(np.unique(sampled_labels)) >= len(sampled_labels):
        return {"silhouette": float("nan"), "davies_bouldin": float("nan"), "calinski_harabasz": float("nan")}
    sample = features[indices]
    if hasattr(sample, "toarray"):
        sample = sample.toarray()
    return {
        "silhouette": float(silhouette_score(sample, sampled_labels)),
        "davies_bouldin": float(davies_bouldin_score(sample, sampled_labels)),
        "calinski_harabasz": float(calinski_harabasz_score(sample, sampled_labels)),
    }


def choose_k(features_train: Any, features_val: Any, k_values: list[int], sample_size: int,
             seed: int) -> tuple[MiniBatchKMeans, int, list[dict[str, float]]]:
    """Select k by validation silhouette; ties prefer the smaller value."""
    candidate_rows = []
    rng = np.random.default_rng(seed)
    n_train, n_val = features_train.shape[0], features_val.shape[0]
    indices = rng.choice(n_val, min(n_val, sample_size), replace=False)
    for k in sorted(set(int(value) for value in k_values if 1 < value < n_train)):
        model = fit_kmeans(features_train, k, seed)
        val_labels = model.predict(features_val)
        sample_labels = val_labels[indices]
        sample_features = features_val[indices]
        if len(np.unique(sample_labels)) < 2 or len(np.unique(sample_labels)) >= len(sample_labels):
            silhouette = float("nan")
            db = float("nan")
        else:
            if hasattr(sample_features, "toarray"):
                sample_features = sample_features.toarray()
            silhouette = float(silhouette_score(sample_features, sample_labels))
            db = float(davies_bouldin_score(sample_features, sample_labels))
        candidate_rows.append({"k": k, "silhouette_val": silhouette, "davies_bouldin_val": db})
    valid = [row for row in candidate_rows if np.isfinite(row["silhouette_val"])]
    if not valid:
        raise ValueError("No valid k produced at least two non-empty validation clusters")
    best_k = max(valid, key=lambda row: (row["silhouette_val"], -row["k"]))["k"]
    best_model = fit_kmeans(features_train, best_k, seed)
    return best_model, best_k, candidate_rows


def split_scores(features: Any, clusters: np.ndarray, has_alert: np.ndarray, alert_tag: np.ndarray,
                 sample_size: int, seed: int) -> dict[str, float]:
    """Combine internal and external scores for a single split."""
    return {
        **internal_metrics(features, clusters, sample_size, seed),
        **external_metrics(clusters, has_alert, alert_tag),
    }


def choose_best_deep(validation: dict[str, dict[str, float]], tolerance: float = 0.01) -> str:
    """Choose the best deep representation using validation silhouette and the specified tie-break."""
    lstm_silhouette = validation["lstm"]["silhouette"]
    gru_silhouette = validation["gru"]["silhouette"]
    if abs(lstm_silhouette - gru_silhouette) <= tolerance:
        return max(("lstm", "gru"), key=lambda name: (validation[name]["nmi_alert_tag"], name == "lstm"))
    return max(("lstm", "gru"), key=lambda name: validation[name]["silhouette"])


def stratified_sample_indices(strata: np.ndarray, sample_size: int, seed: int) -> np.ndarray:
    """Return deterministic indices with class proportions preserved."""
    labels = np.asarray(strata)
    if labels.ndim != 1:
        raise ValueError("strata must be one-dimensional")
    if sample_size < 1 or sample_size > len(labels):
        raise ValueError("sample_size must be between 1 and the number of strata")
    if sample_size == len(labels):
        return np.arange(len(labels))
    splitter = StratifiedShuffleSplit(n_splits=1, train_size=sample_size, random_state=seed)
    indices, _ = next(splitter.split(np.zeros(len(labels)), labels))
    return np.sort(indices)
