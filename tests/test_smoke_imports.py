"""Smoke test: every dependency and the package import, and the config helpers work."""
import importlib

import pytest

MODULES = [
    "bgllog", "torch", "numpy", "pandas", "pyarrow", "scipy", "sklearn", "drain3",
    "mlxtend", "prefixspan", "umap", "matplotlib", "seaborn", "plotly", "streamlit",
    "yaml", "tqdm", "joblib", "requests",
]


@pytest.mark.parametrize("name", MODULES)
def test_import(name):
    importlib.import_module(name)


def test_config_and_seed():
    from bgllog.io import REPO_ROOT, ensure_dirs, get_path, load_config, set_seed

    cfg = load_config()
    assert cfg["seed"] == 42
    assert get_path(cfg, "raw_dir") == REPO_ROOT / "data" / "raw"
    ensure_dirs(cfg)
    set_seed(cfg["seed"])
