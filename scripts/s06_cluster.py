"""Fit leakage-safe clusters, compare representations, and write S06 artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import HDBSCAN
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.metrics import normalized_mutual_info_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import TruncatedSVD

from bgllog.clustering import (choose_best_deep, choose_k, event_count_matrix,
                               external_metrics, fit_kmeans, internal_metrics,
                               stratified_sample_indices)
from bgllog.io import REPO_ROOT, load_config


def _savefig(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _load_features(name: str, splits: dict[str, np.ndarray], vocab_size: int, cfg: dict,
                   sample: bool) -> tuple[dict[str, object], dict]:
    if name in ("bow", "tfidf_svd"):
        counts = {split: event_count_matrix(windows, vocab_size) for split, windows in splits.items()}
        if name == "bow":
            return counts, {"kind": "bow"}
        transformer = TfidfTransformer(norm="l2", use_idf=True)
        train_tfidf = transformer.fit_transform(counts["train"])
        dims = min(int(cfg["clustering"]["svd_dims"]), counts["train"].shape[1] - 1, len(splits["train"]) - 1)
        reducer = TruncatedSVD(n_components=dims, n_iter=7, random_state=cfg["seed"])
        train = reducer.fit_transform(train_tfidf).astype(np.float32)
        val = reducer.transform(transformer.transform(counts["val"])).astype(np.float32)
        test = reducer.transform(transformer.transform(counts["test"])).astype(np.float32)
        return {"train": train, "val": val, "test": test}, {
            "kind": "tfidf_svd", "tfidf": transformer, "svd": reducer,
        }

    embed_root = REPO_ROOT / "artifacts" / "embeddings"
    values = {
        split: np.load(embed_root / f"{name}_{split}.npy", mmap_mode="r")[:len(splits[split])]
        for split in splits
    }
    scaler = StandardScaler()
    train = scaler.fit_transform(np.asarray(values["train"], dtype=np.float32))
    val = scaler.transform(np.asarray(values["val"], dtype=np.float32))
    test = scaler.transform(np.asarray(values["test"], dtype=np.float32))
    return {"train": train, "val": val, "test": test}, {"kind": "scaled", "scaler": scaler}


def _plot_sweep(sweep: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    sns.lineplot(data=sweep, x="k", y="silhouette_val", hue="representation", marker="o", ax=axes[0])
    sns.lineplot(data=sweep, x="k", y="davies_bouldin_val", hue="representation", marker="o", ax=axes[1])
    axes[0].set_title("Silhouette validation")
    axes[1].set_title("Davies–Bouldin validation (lebih rendah lebih baik)")
    axes[0].set_xlabel("Jumlah cluster (k)")
    axes[1].set_xlabel("Jumlah cluster (k)")
    _savefig(fig, path)


def _profile_clusters(features_test: np.ndarray, labels: np.ndarray, windows: np.ndarray,
                      global_windows: np.ndarray, metadata: pd.DataFrame, vocab: dict,
                      templates: pd.DataFrame) -> list[dict]:
    index_to_event = {int(index): int(event) for event, index in vocab.items()}
    event_templates = {int(row.event_id): str(row.template) for row in templates.itertuples()}
    global_counts = np.bincount(global_windows.reshape(-1), minlength=max(index_to_event, default=1) + 1)[2:].astype(float)
    global_total = global_counts.sum()
    profiles = []
    for cluster in sorted(np.unique(labels)):
        mask = labels == cluster
        member_windows = windows[mask]
        counts = np.bincount(member_windows.reshape(-1), minlength=len(global_counts) + 2)[2:].astype(float)
        total_events = max(counts.sum(), 1.0)
        frequencies = counts / total_events
        global_frequency = global_counts / max(global_total, 1.0)
        lift = frequencies / np.maximum(global_frequency, 1e-12)
        top_freq = np.argsort(counts)[::-1][:10]
        top_lift = np.argsort(lift)[::-1][:10]
        member_features = features_test[mask]
        centroid = member_features.mean(axis=0)
        representative_idx = np.argmin(((member_features - centroid) ** 2).sum(axis=1))
        representative = member_windows[representative_idx]
        tag_counts = metadata.loc[mask, "alert_tag"].astype(str).value_counts().head(3)
        alerts = metadata.loc[mask, "has_alert"].astype(bool)
        cluster_profile = {
            "cluster": int(cluster),
            "size": int(mask.sum()),
            "share": float(mask.mean()),
            "alert_window_rate": float(alerts.mean()),
            "top_alert_tags": [{"tag": tag, "count": int(count)} for tag, count in tag_counts.items()],
            "top_events_by_frequency": [
                {"event_id": index_to_event.get(int(i + 2)), "template": event_templates.get(index_to_event.get(int(i + 2)), ""),
                 "count": int(counts[i]), "frequency": float(frequencies[i])}
                for i in top_freq if i < len(counts) and counts[i] > 0
            ],
            "top_events_by_lift": [
                {"event_id": index_to_event.get(int(i + 2)), "template": event_templates.get(index_to_event.get(int(i + 2)), ""),
                 "lift": float(lift[i]), "frequency": float(frequencies[i])}
                for i in top_lift if i < len(lift) and counts[i] > 0
            ],
            "mean_ts_start": float(metadata.loc[mask, "ts_start"].mean()),
            "representative_events": [
                {"event_id": index_to_event.get(int(token)), "template": event_templates.get(index_to_event.get(int(token)), "<PAD/UNK>")}
                for token in representative if int(token) > 1
            ],
        }
        profiles.append(cluster_profile)
    return profiles


def _hdbscan(best_features: dict, labels: dict, cfg: dict, seed: int,
             output_path: Path, kmeans_labels: np.ndarray) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    import umap

    settings = cfg["clustering"]["hdbscan"]
    rng = np.random.default_rng(seed)
    train = best_features["train"]
    count = min(int(settings["subsample"]), len(train))
    indices = stratified_sample_indices(labels["has_alert"]["train"], count, seed)
    reducer = umap.UMAP(n_components=cfg["clustering"]["umap_dims"], n_neighbors=30, min_dist=0.0,
                        metric="euclidean", random_state=seed, transform_seed=seed)
    train_umap = reducer.fit_transform(train[indices])
    clusterer = HDBSCAN(min_cluster_size=int(settings["min_cluster_size"]), metric="euclidean")
    fitted_labels = clusterer.fit_predict(train_umap)

    test_umap = reducer.transform(best_features["test"])
    finite_test = np.isfinite(test_umap).all(axis=1)
    test_labels = np.full(len(test_umap), -1, dtype=np.int32)
    if finite_test.any():
        if hasattr(clusterer, "predict"):
            test_labels[finite_test] = clusterer.predict(test_umap[finite_test])
        else:
            nearest = NearestNeighbors(n_neighbors=1, metric="euclidean").fit(train_umap)
            nearest_index = nearest.kneighbors(test_umap[finite_test], return_distance=False).ravel()
            test_labels[finite_test] = fitted_labels[nearest_index]

    noise_ratio = float(np.mean(test_labels == -1))
    metrics = {
        "representation": "best_deep",
        "algorithm": "HDBSCAN",
        "k": int(len(set(fitted_labels)) - (1 if -1 in fitted_labels else 0)),
        **internal_metrics(test_umap[finite_test], test_labels[finite_test],
                           int(cfg["clustering"]["silhouette_sample"]), seed),
        **external_metrics(test_labels, labels["has_alert"]["test"], labels["alert_tag"]["test"]),
        "noise_ratio": noise_ratio,
        "unprojectable_ratio": float(np.mean(~np.isfinite(test_umap).all(axis=1))),
        "alert_window_rate": float(np.mean(labels["has_alert"]["test"])),
        "split": "test",
        "seeds_checked": 1,
        "nmi_alert_std": 0.0,
        "ari_alert_std": 0.0,
    }

    plot_count = min(int(cfg["clustering"]["umap_plot_sample"]), len(best_features["test"]))
    plot_indices = stratified_sample_indices(labels["has_alert"]["test"], plot_count, seed)
    plot_reducer = umap.UMAP(n_components=2, n_neighbors=30, min_dist=0.0, metric="euclidean",
                             random_state=seed, transform_seed=seed)
    plot_train_count = min(int(cfg["clustering"]["umap_plot_sample"]), len(train))
    plot_train_indices = np.sort(rng.choice(len(train), plot_train_count, replace=False))
    plot_reducer.fit(train[plot_train_indices])
    coordinates = plot_reducer.transform(best_features["test"][plot_indices]).astype(np.float32)
    finite_plot = np.isfinite(coordinates).all(axis=1)
    plot_indices = plot_indices[finite_plot]
    coordinates = coordinates[finite_plot]
    np.savez_compressed(
        output_path,
        coordinates=coordinates,
        cluster=kmeans_labels[plot_indices].astype(np.int32),
        has_alert=labels["has_alert"]["test"][plot_indices],
        alert_tag=labels["alert_tag"]["test"][plot_indices].astype(str),
    )
    return metrics, test_labels, coordinates, plot_indices


def run(config_path: str = "configs/default.yaml", sample: bool = False) -> dict:
    cfg = load_config(config_path)
    seed = int(cfg["seed"])
    data_root = REPO_ROOT / "data" / "processed"
    metadata = pd.read_parquet(data_root / "windows_meta.parquet")
    windows_all = np.load(data_root / "windows_X.npy", mmap_mode="r")
    train_data = np.load(REPO_ROOT / "handoff" / "windows.npz")
    splits = {name: train_data[f"X_{name}"] for name in ("train", "val", "test")}
    split_meta = {name: metadata.loc[metadata["split"] == name].reset_index(drop=True)
                  for name in ("train", "val", "test")}

    if sample:
        limits = {"train": 5000, "val": 2000, "test": 2000}
        splits = {name: values[:limits[name]] for name, values in splits.items()}
        split_meta = {name: frame.iloc[:limits[name]].copy() for name, frame in split_meta.items()}
        windows_all = np.concatenate(list(splits.values()), axis=0)
        out_root = REPO_ROOT / "artifacts" / "sample" / "clusters"
        report_root = REPO_ROOT / "reports" / "sample"
    else:
        out_root = REPO_ROOT / "artifacts" / "clusters"
        report_root = REPO_ROOT / "reports"
    out_root.mkdir(parents=True, exist_ok=True)
    (report_root / "tables").mkdir(parents=True, exist_ok=True)
    (report_root / "figures").mkdir(parents=True, exist_ok=True)

    if any(len(splits[name]) != len(split_meta[name]) for name in splits):
        raise ValueError("handoff windows and windows_meta split rows do not align")
    if not sample and len(windows_all) != len(metadata):
        raise ValueError("windows_X.npy and windows_meta.parquet do not align")
    if not sample and len(splits["train"]) + len(splits["val"]) + len(splits["test"]) != len(metadata) - int((metadata["split"] == "gap").sum()):
        raise ValueError("handoff split sizes do not match windows_meta.parquet")

    labels = {
        "has_alert": {name: frame["has_alert"].to_numpy(dtype=bool) for name, frame in split_meta.items()},
        "alert_tag": {name: frame["alert_tag"].astype(str).to_numpy() for name, frame in split_meta.items()},
    }
    vocab_data = json.loads((REPO_ROOT / "artifacts" / "vocab.json").read_text(encoding="utf-8"))
    vocab = {int(event): int(index) for event, index in vocab_data["event_to_index"].items()}
    vocab_size = int(train_data["vocab_size"])
    del train_data
    templates = pd.read_csv(data_root / "templates.csv")
    representations = ("bow", "tfidf_svd", "lstm", "gru")
    k_values = list(cfg["clustering"]["k_values"])
    if sample:
        k_values = [k for k in k_values if k <= 16]
    sweep_rows, metrics_rows, chosen, best_validation, best_features, test_clusters = [], [], {}, {}, {}, {}
    for name in representations:
        feature_splits, transform = _load_features(name, splits, vocab_size, cfg, sample)
        model, best_k, sweep = choose_k(
            feature_splits["train"], feature_splits["val"], k_values,
            int(cfg["clustering"]["silhouette_sample"]), seed,
        )
        for row in sweep:
            sweep_rows.append({"representation": name, **row})
        val_prediction = model.predict(feature_splits["val"])
        val_external = external_metrics(val_prediction, labels["has_alert"]["val"], labels["alert_tag"]["val"])
        best_validation[name] = {
            "silhouette": next(row["silhouette_val"] for row in sweep if row["k"] == best_k),
            "nmi_alert_tag": val_external["nmi_alert_tag"],
        }

        seed_results = []
        test_prediction = None
        chosen_model = None
        for model_seed in cfg["clustering"]["seeds"]:
            repeat = model if int(model_seed) == seed else fit_kmeans(feature_splits["train"], best_k, int(model_seed))
            prediction = repeat.predict(feature_splits["test"])
            seed_metrics = external_metrics(prediction, labels["has_alert"]["test"], labels["alert_tag"]["test"])
            seed_results.append(seed_metrics)
            if int(model_seed) == seed:
                chosen_model, test_prediction = repeat, prediction

        test_scores = {
            **internal_metrics(feature_splits["test"], test_prediction,
                               int(cfg["clustering"]["silhouette_sample"]), seed),
            **seed_results[0],
        }
        test_scores["nmi_alert_mean"] = float(np.mean([row["nmi_alert"] for row in seed_results]))
        test_scores["nmi_alert_std"] = float(np.std([row["nmi_alert"] for row in seed_results]))
        test_scores["ari_alert_mean"] = float(np.mean([row["ari_alert"] for row in seed_results]))
        test_scores["ari_alert_std"] = float(np.std([row["ari_alert"] for row in seed_results]))
        test_scores["alert_window_rate"] = float(np.mean(labels["has_alert"]["test"]))
        test_scores.update({"representation": name, "algorithm": "MiniBatchKMeans", "k": best_k,
                            "split": "test", "seeds_checked": len(seed_results)})
        metrics_rows.append(test_scores)
        test_clusters[name] = test_prediction
        chosen[name] = {"model": chosen_model, "k": best_k, **transform}
        joblib.dump(chosen[name], out_root / f"kmeans_{name}.joblib", compress=3)
        if name in ("lstm", "gru"):
            best_features[name] = feature_splits
        del feature_splits

    best_deep = choose_best_deep(best_validation)
    best_model = chosen[best_deep]["model"]
    best_prediction = best_model.predict(best_features[best_deep]["test"])
    hdbscan_metrics, _, coordinates, plot_indices = _hdbscan(
        best_features[best_deep], labels, cfg, seed, out_root / "umap_sample.npz", best_prediction,
    )
    hdbscan_metrics["representation"] = best_deep
    metrics_rows.append(hdbscan_metrics)

    if not sample:
        # Profile the test windows, which have not influenced model selection or fitting.
        test_profiles = _profile_clusters(
            best_features[best_deep]["test"], best_prediction, splits["test"], windows_all,
            split_meta["test"], vocab, templates,
        )
        (out_root / "cluster_profiles.json").write_text(json.dumps(test_profiles, indent=2) + "\n", encoding="utf-8")
        pd.DataFrame([{
            "cluster": profile["cluster"],
            "size": profile["size"],
            "share": profile["share"],
            "alert_window_rate": profile["alert_window_rate"],
            "mean_ts_start": profile["mean_ts_start"],
            "top_alert_tags": " | ".join(item["tag"] for item in profile["top_alert_tags"]),
            "top_events": " | ".join(item["template"] for item in profile["top_events_by_frequency"][:3]),
        } for profile in test_profiles]).to_csv(report_root / "tables" / "cluster_profiles.csv", index=False)

    sweep = pd.DataFrame(sweep_rows)
    metrics = pd.DataFrame(metrics_rows)
    sweep.to_csv(report_root / "tables" / "clustering_k_sweep.csv", index=False)
    metrics.to_csv(report_root / "tables" / "clustering_metrics.csv", index=False)
    _plot_sweep(sweep, report_root / "figures" / "clu_k_sweep.png")

    sample_data = np.load(out_root / "umap_sample.npz")
    sample_clusters = sample_data["cluster"]
    sample_alerts = sample_data["has_alert"]
    plot_labels = sample_data["alert_tag"]
    sample_coords = sample_data["coordinates"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].scatter(sample_coords[:, 0], sample_coords[:, 1], c=sample_clusters, s=3, cmap="tab20")
    axes[0].set_title(f"UMAP test windows: cluster ({best_deep})")
    axes[1].scatter(sample_coords[:, 0], sample_coords[:, 1], c=sample_alerts.astype(int), s=3,
                     cmap="coolwarm", vmin=0, vmax=1)
    axes[1].set_title("UMAP test windows: alert / non-alert")
    for ax in axes:
        ax.set_xlabel("UMAP 1")
        ax.set_ylabel("UMAP 2")
    _savefig(fig, report_root / "figures" / "clu_umap_clusters.png")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(sample_coords[:, 0], sample_coords[:, 1], c=sample_alerts.astype(int), s=3,
               cmap="coolwarm", vmin=0, vmax=1)
    ax.set_title("UMAP test windows: alert / non-alert")
    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")
    _savefig(fig, report_root / "figures" / "clu_umap_alerts.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    alert_rates = [row["alert_window_rate"] for row in test_profiles] if not sample else []
    if alert_rates:
        ax.bar([row["cluster"] for row in test_profiles], alert_rates, color="#E45756")
        ax.set_xlabel("Cluster")
        ax.set_ylabel("Proporsi jendela ber-alert")
    ax.set_title("Tingkat alert per cluster")
    _savefig(fig, report_root / "figures" / "clu_cluster_alert_rate.png")

    confusion = pd.crosstab(pd.Series(plot_labels, name="Tag alert"), pd.Series(sample_clusters, name="Cluster"),
                            normalize="columns")
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(confusion, cmap="Blues", ax=ax)
    ax.set_title("Komposisi tag alert per cluster (sampel test)")
    _savefig(fig, report_root / "figures" / "clu_confusion_tag_vs_cluster.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    validation_frame = pd.DataFrame([
        {"representation": name, **values} for name, values in best_validation.items()
    ])
    sns.barplot(data=validation_frame, x="representation", y="silhouette", ax=ax, color="#4C78A8")
    ax.set_title("Perbandingan silhouette pada validation")
    ax.set_xlabel("Representasi")
    ax.set_ylabel("Silhouette")
    _savefig(fig, report_root / "figures" / "clu_representation_comparison.png")

    results = {
        "metrics": metrics_rows,
        "best_deep_representation": best_deep,
        "validation": best_validation,
    }
    if not sample:
        results_path = REPO_ROOT / "reports" / "results.json"
        report_results = json.loads(results_path.read_text(encoding="utf-8"))
        report_results["clustering"] = metrics_rows
        shuffled = {}
        for representation in ("bow", "tfidf_svd", "lstm", "gru"):
            clusters = test_clusters[representation]
            rng = np.random.default_rng(seed)
            shuffled[representation] = {
                "has_alert": float(normalized_mutual_info_score(
                    rng.permutation(labels["has_alert"]["test"]), clusters)),
                "alert_tag": float(normalized_mutual_info_score(
                    rng.permutation(labels["alert_tag"]["test"]), clusters)),
            }
        report_results.setdefault("sanity", {})["shuffled_label_nmi"] = shuffled
        report_results["clustering_summary"] = results
        results_path.write_text(json.dumps(report_results, indent=2) + "\n", encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    result = run(args.config, args.sample)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
