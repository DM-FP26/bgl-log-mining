"""Training loop for the next-event LSTM/GRU: checkpoints, resume, evaluation. Works on CPU or CUDA."""
from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import yaml

from bgllog.io import REPO_ROOT, set_seed
from bgllog.models import LogRNN, build_model

UNK = 1


def load_windows(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    return {"X_train": z["X_train"], "X_val": z["X_val"], "X_test": z["X_test"],
            "vocab_size": int(z["vocab_size"]), "meta": meta}


def pick_device(requested: str) -> torch.device:
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit("ERROR: --device cuda requested but CUDA is not available. "
                             "Run scripts/check_gpu.py and see docs/GPU-HANDOFF-FRIEND.md. No silent fallback to CPU.")
        return torch.device("cuda")
    if requested == "cpu":
        return torch.device("cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def next_event_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Cross-entropy over all positions; PAD (0) targets are ignored."""
    return F.cross_entropy(logits.reshape(-1, logits.size(-1)), target.reshape(-1), ignore_index=0)


@torch.no_grad()
def evaluate(model: LogRNN, X: np.ndarray, device: torch.device, batch_size: int = 2048) -> dict:
    """Loss, perplexity, top-1 and top-5 next-event accuracy (PAD targets excluded)."""
    model.eval()
    tot_loss, n, c1, c5, n_ch, c1_ch = 0.0, 0, 0, 0, 0, 0
    k = min(5, model.cfg["vocab_size"])
    for i in range(0, len(X), batch_size):
        xb = torch.from_numpy(X[i: i + batch_size].astype(np.int64)).to(device)
        logits = model(xb[:, :-1])
        tgt = xb[:, 1:]
        m = tgt != 0
        if m.sum() == 0:
            continue
        lp = F.cross_entropy(logits.reshape(-1, logits.size(-1)), tgt.reshape(-1), ignore_index=0, reduction="sum")
        topk = logits.topk(k, dim=-1).indices
        hit = topk == tgt.unsqueeze(-1)
        tot_loss += float(lp); n += int(m.sum())
        c1 += int((hit[..., 0] & m).sum()); c5 += int((hit.any(-1) & m).sum())
        ch = m & (tgt != xb[:, :-1])                              # positions where the next event differs from the current one
        n_ch += int(ch.sum()); c1_ch += int((hit[..., 0] & ch).sum())
    if n == 0:
        return {"loss": float("nan"), "perplexity": float("nan"), "top1": float("nan"), "top5": float("nan"), "top1_on_changes": float("nan"), "n_change_tokens": 0, "n_tokens": 0, "n_windows": int(len(X))}
    loss = tot_loss / n
    return {"loss": loss, "perplexity": float(np.exp(loss)), "top1": c1 / n, "top5": c5 / n,
            "top1_on_changes": (c1_ch / n_ch) if n_ch else float("nan"), "n_change_tokens": n_ch, "n_tokens": n, "n_windows": int(len(X))}


def unk_free_mask(X: np.ndarray) -> np.ndarray:
    """Windows that contain no UNK token (S02 decision: report the test split both ways)."""
    return ~(X == UNK).any(axis=1)


def _env_info(device: torch.device, rnn_type: str, resolved_cfg: dict, windows_hash: str) -> dict:
    info = {"torch": torch.__version__, "cuda_available": torch.cuda.is_available(), "cuda_version": torch.version.cuda,
            "device_used": str(device), "gpu_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
            "arch_list": torch.cuda.get_arch_list() if torch.cuda.is_available() else [],
            "python": sys.version.split()[0], "platform": platform.platform(), "model_type": rnn_type,
            "windows_meta_hash": windows_hash, "config": resolved_cfg}
    return info


def run(cfg: dict, model_type: str, device_req: str = "auto", epochs: int | None = None,
        max_train_windows: int | None = None, resume: bool = False, out: str | Path = "handoff/results/lstm",
        batch_size: int | None = None) -> dict:
    """Train, validate every epoch, then evaluate once on the test split. Returns the test metrics."""
    out = Path(out)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    device = pick_device(device_req)
    tcfg = cfg["train"]
    epochs = epochs or tcfg["epochs"]
    batch_size = batch_size or tcfg["batch_size"]
    seed = cfg.get("seed", 42)
    set_seed(seed)
    if device.type == "cuda":
        print(f"=== DEVICE: CUDA, {torch.cuda.get_device_name(0)} ===", flush=True)
    else:
        print("=== DEVICE: CPU (no GPU in use) ===", flush=True)

    data = load_windows(cfg["data"]["windows_path"])
    X_train, X_val, X_test, vocab_size = data["X_train"], data["X_val"], data["X_test"], data["vocab_size"]
    if max_train_windows:
        X_train = X_train[:max_train_windows]
    resolved = {**cfg, "model": {**cfg["model"], "type": model_type}, "train": {**tcfg, "epochs": epochs, "batch_size": batch_size},
                "device": str(device), "max_train_windows": max_train_windows}
    env = _env_info(device, model_type, resolved, data["meta"].get("config_hash", ""))
    (out / "env.json").write_text(json.dumps(env, indent=2))

    model = build_model(cfg["model"], vocab_size, model_type).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=tcfg["lr"], weight_decay=tcfg.get("weight_decay", 0.0))
    (out / "config.json").write_text(json.dumps({"model": model.cfg, "windows_meta": data["meta"], "pooling": cfg["embed"]["pooling"]}, indent=2))

    history: list[dict] = []
    best_val, bad_epochs, start_epoch, finished = float("inf"), 0, 0, False
    last_path = out / "last.pt"
    if resume and last_path.exists():
        ck = torch.load(last_path, map_location=device, weights_only=False)
        model.load_state_dict(ck["model"]); opt.load_state_dict(ck["optimizer"])
        start_epoch, best_val, bad_epochs = ck["epoch"], ck["best_val"], ck["bad_epochs"]
        history, finished = ck["history"], ck.get("stopped_early", False)
        print(f"Resuming from epoch {start_epoch} (best val loss {best_val:.4f})", flush=True)

    Xt = torch.from_numpy(X_train.astype(np.int64)).to(device)   # the whole train set is small; keep it on the device
    g = torch.Generator().manual_seed(seed)
    for ep in range(start_epoch, 0 if finished else epochs):
        t0 = time.time()
        model.train()
        g.manual_seed(seed + ep)                                  # same shuffle whether resumed or not
        perm = torch.randperm(len(Xt), generator=g).to(device)
        run_loss, steps = 0.0, 0
        for i in range(0, len(Xt), batch_size):
            xb = Xt[perm[i: i + batch_size]]
            loss = next_event_loss(model(xb[:, :-1]), xb[:, 1:])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), tcfg["grad_clip"])
            opt.step()
            run_loss += float(loss); steps += 1
        val = evaluate(model, X_val, device)
        row = {"epoch": ep + 1, "train_loss": run_loss / max(steps, 1), "val_loss": val["loss"], "val_top1": val["top1"],
               "val_top5": val["top5"], "seconds": round(time.time() - t0, 1)}
        history.append(row)
        print(f"[{model_type}] epoch {row['epoch']}/{epochs} train {row['train_loss']:.4f} val {row['val_loss']:.4f} "
              f"top1 {row['val_top1']:.4f} ({row['seconds']}s)", flush=True)
        if val["loss"] < best_val:
            best_val, bad_epochs = val["loss"], 0
            torch.save({"model": model.state_dict(), "cfg": model.cfg, "epoch": ep + 1, "val_loss": best_val}, out / "best.pt")
        else:
            bad_epochs += 1
        stop = bad_epochs >= tcfg["early_stop_patience"]
        torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(), "epoch": ep + 1, "best_val": best_val,
                    "bad_epochs": bad_epochs, "history": history, "stopped_early": stop}, last_path)
        pd.DataFrame(history).to_csv(out / "history.csv", index=False)
        if stop:
            print(f"Early stopping at epoch {ep + 1} (patience {tcfg['early_stop_patience']})", flush=True)
            break

    # ---- one-time test evaluation with the BEST checkpoint --------------------------------------
    if not (out / "best.pt").exists():
        raise SystemExit("ERROR: no best.pt was produced (no epoch ran).")
    ck = torch.load(out / "best.pt", map_location=device, weights_only=False)
    model.load_state_dict(ck["model"])
    free = unk_free_mask(X_test)
    metrics = {"model": model_type, "best_epoch": ck["epoch"], "best_val_loss": ck["val_loss"],
               "test": evaluate(model, X_test, device),
               "test_unk_free": evaluate(model, X_test[free], device),
               "val": evaluate(model, X_val, device),
               "n_params": int(sum(p.numel() for p in model.parameters())), "epochs_run": len(history),
               "device": str(device), "seed": seed}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print("TEST (all windows):", {k: round(v, 4) if isinstance(v, float) else v for k, v in metrics["test"].items()}, flush=True)
    print("TEST (UNK-free windows):", {k: round(v, 4) if isinstance(v, float) else v for k, v in metrics["test_unk_free"].items()}, flush=True)
    return metrics
