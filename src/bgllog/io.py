"""Config loading, path helpers, logging setup and seeding.

Every path and hyperparameter comes from ``configs/default.yaml``; nothing is hard-coded.
"""
from __future__ import annotations

import logging
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yaml"


def load_config(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load a YAML config. A relative path is resolved against the repo root."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    if not cfg_path.is_absolute():
        cfg_path = REPO_ROOT / cfg_path
    with cfg_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_path(cfg: dict[str, Any], key: str) -> Path:
    """Return the absolute path for a key under ``cfg['paths']`` (for example ``raw_dir``)."""
    return REPO_ROOT / cfg["paths"][key]


def ensure_dirs(cfg: dict[str, Any]) -> None:
    """Create every directory listed under ``cfg['paths']``."""
    for key in cfg["paths"]:
        get_path(cfg, key).mkdir(parents=True, exist_ok=True)


def get_logger(stage: str, cfg: dict[str, Any] | None = None) -> logging.Logger:
    """Logger that writes INFO to the console and to ``logs/<stage>.log``."""
    cfg = cfg or load_config()
    logger = logging.getLogger(stage)
    if logger.handlers:  # already configured (idempotent)
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)
    logs_dir = get_path(cfg, "logs_dir")
    logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(logs_dir / f"{stage}.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


def set_seed(seed: int) -> None:
    """Seed python, numpy and (if installed) torch."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass
