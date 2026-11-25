"""Train an LSTM or GRU next-event model.

    python scripts/train.py --config configs/train.yaml --model lstm|gru
        [--device auto|cpu|cuda] [--epochs N] [--max-train-windows N] [--batch-size N] [--resume] [--out DIR]
"""
from __future__ import annotations

import argparse
import sys

import yaml

from bgllog.io import REPO_ROOT
from bgllog.train import run


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="configs/train.yaml")
    ap.add_argument("--model", required=True, choices=["lstm", "gru"])
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--max-train-windows", type=int)
    ap.add_argument("--batch-size", type=int)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    cfg_path = REPO_ROOT / a.config if not a.config.startswith("/") else a.config
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    run(cfg, a.model, a.device, a.epochs, a.max_train_windows, a.resume, a.out or f"handoff/results/{a.model}", a.batch_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
