"""Copy trained models into the app artifacts and extract embeddings on CPU."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import yaml
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bgllog.embed import embed_windows
from bgllog.io import REPO_ROOT
from bgllog.models import build_model
from bgllog.train import load_windows


def mean_window_loss(model: torch.nn.Module, windows: np.ndarray, batch_size: int) -> np.ndarray:
    model.eval()
    losses = []
    with torch.no_grad():
        for start in range(0, len(windows), batch_size):
            batch = torch.from_numpy(windows[start:start + batch_size].astype(np.int64))
            logits = model(batch[:, :-1])
            targets = batch[:, 1:]
            token_loss = F.cross_entropy(
                logits.transpose(1, 2), targets, reduction="none", ignore_index=0
            )
            mask = targets != 0
            per_window = (token_loss * mask).sum(1) / mask.sum(1).clamp(min=1)
            losses.append(per_window.cpu().numpy().astype(np.float32))
    return np.concatenate(losses) if losses else np.zeros(0, dtype=np.float32)


def process_model(name: str, splits: dict[str, np.ndarray], batch_size: int, force: bool) -> dict:
    source = REPO_ROOT / "handoff" / "results" / name
    required = ("best.pt", "config.json", "history.csv", "metrics.json", "env.json")
    missing = [file for file in required if not (source / file).is_file()]
    if missing:
        raise FileNotFoundError(f"{source} is missing: {', '.join(missing)}")

    model_config = json.loads((source / "config.json").read_text(encoding="utf-8"))
    cfg = model_config["model"]
    model = build_model(cfg, int(cfg["vocab_size"]), name)
    checkpoint = torch.load(source / "best.pt", map_location="cpu", weights_only=False)
    model.load_state_dict(checkpoint["model"])
    model.eval()

    model_out = REPO_ROOT / "artifacts" / "models" / name
    model_out.mkdir(parents=True, exist_ok=True)
    for file in ("best.pt", "config.json", "history.csv", "metrics.json"):
        target = model_out / file
        if target.exists() and not force:
            raise FileExistsError(f"{target} exists; pass --force to replace it")
        shutil.copy2(source / file, target)

    embed_out = REPO_ROOT / "artifacts" / "embeddings"
    embed_out.mkdir(parents=True, exist_ok=True)
    pooling = model_config.get("pooling", "mean")
    all_losses = []
    for split_name, windows in splits.items():
        embedding_path = embed_out / f"{name}_{split_name}.npy"
        if not force and embedding_path.exists():
            raise FileExistsError(f"{embedding_path} exists; pass --force to replace it")
        embeddings = embed_windows(model, windows, pooling=pooling, batch_size=batch_size, device="cpu")
        losses = mean_window_loss(model, windows, batch_size)
        if embeddings.shape != (len(windows), int(cfg["hidden_dim"])):
            raise ValueError(f"{name}/{split_name} embedding shape is {embeddings.shape}")
        if not np.isfinite(embeddings).all() or not np.isfinite(losses).all():
            raise ValueError(f"{name}/{split_name} produced non-finite output")
        np.save(embedding_path, embeddings)
        all_losses.append(losses)
    window_loss_path = embed_out / f"{name}_window_loss.npy"
    if window_loss_path.exists() and not force:
        raise FileExistsError(f"{window_loss_path} exists; pass --force to replace it")
    np.save(window_loss_path, np.concatenate(all_losses))

    history = pd.read_csv(source / "history.csv")
    metrics = json.loads((source / "metrics.json").read_text(encoding="utf-8"))
    env = json.loads((source / "env.json").read_text(encoding="utf-8"))
    result = {
        **metrics,
        "epochs_trained": int(len(history)),
        "training_seconds": float(history["seconds"].sum()),
        "device_name": env.get("gpu_name"),
        "cuda": env.get("cuda_version"),
    }
    return result


def write_report_outputs(results: dict) -> None:
    report_root = REPO_ROOT / "reports"
    figure_root, table_root = report_root / "figures", report_root / "tables"
    figure_root.mkdir(parents=True, exist_ok=True)
    table_root.mkdir(parents=True, exist_ok=True)
    histories = {
        name: pd.read_csv(REPO_ROOT / "handoff" / "results" / name / "history.csv")
        for name in ("lstm", "gru")
    }
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for name, history in histories.items():
        axes[0].plot(history["epoch"], history["train_loss"], label=f"{name.upper()} train")
        axes[0].plot(history["epoch"], history["val_loss"], linestyle="--", label=f"{name.upper()} val")
        axes[1].plot(history["epoch"], history["val_loss"], label=name.upper())
    axes[0].set_title("Loss training dan validation")
    axes[1].set_title("Perbandingan loss validation")
    for ax in axes:
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.legend()
    fig.tight_layout()
    fig.savefig(figure_root / "dl_loss_curves.png", dpi=200)
    plt.close(fig)

    baseline = results["dl"]["baselines"]
    rows = []
    for name in ("lstm", "gru"):
        metrics = results["dl"][name]
        rows.append({
            "model": name,
            "split": "test_all",
            "top1": metrics["test"]["top1"],
            "top5": metrics["test"]["top5"],
            "top1_on_changes": metrics["test"]["top1_on_changes"],
            "loss": metrics["test"]["loss"],
            "epochs_trained": metrics["epochs_trained"],
            "training_seconds": metrics["training_seconds"],
            "device": metrics["device_name"],
        })
        rows.append({
            "model": name,
            "split": "test_unk_free",
            "top1": metrics["test_unk_free"]["top1"],
            "top5": metrics["test_unk_free"]["top5"],
            "top1_on_changes": metrics["test_unk_free"]["top1_on_changes"],
            "loss": metrics["test_unk_free"]["loss"],
            "epochs_trained": metrics["epochs_trained"],
            "training_seconds": metrics["training_seconds"],
            "device": metrics["device_name"],
        })
    for name, score in (("bigram", baseline["bigram_top1"]),
                        ("repeat_last", baseline["repeat_last_top1"])):
        rows.append({"model": name, "split": "test_all", "top1": score})
    pd.DataFrame(rows).to_csv(table_root / "dl_model_comparison.csv", index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/train.yaml")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    cfg = yaml.safe_load((REPO_ROOT / args.config).open(encoding="utf-8"))
    batch_size = args.batch_size or cfg.get("embed", {}).get("batch_size", 4096)
    data = load_windows(cfg["data"]["windows_path"])
    splits = {name: data[f"X_{name}"] for name in ("train", "val", "test")}
    results_path = REPO_ROOT / "reports" / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    results.setdefault("dl", {})
    for name in ("lstm", "gru"):
        metrics = process_model(name, splits, batch_size, args.force)
        results["dl"][name] = metrics
        print(f"{name}: {metrics['epochs_trained']} epochs, {metrics['device_name']}")
    results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    write_report_outputs(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
