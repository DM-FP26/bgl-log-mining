# S00. Setup and scaffolding

## Goal
A clean, runnable repo skeleton with a working Python environment, config, logging and a passing smoke test, pushed to a GitHub repo (public; Nafi approved).

## Depends on
Nothing. Read `CLAUDE.md` and `docs/02-environment-windows.md` first.

## Inputs
- The blueprint files already in the repo root (`CLAUDE.md`, `docs/`, `starter/`).

## Outputs
- Repo layout from `docs/00-overview.md` §4 (empty folders get a `.gitkeep`).
- Files copied from `starter/` to their final places: `.gitignore`, `.gitattributes`, `requirements.txt`, `requirements-train.txt`, `configs/default.yaml`, `configs/train.yaml`.
- `pyproject.toml` (minimal, makes `src/bgllog` installable with `pip install -e .`).
- `src/bgllog/__init__.py`, `src/bgllog/io.py` (config loading, path helpers, logging setup, seeding).
- `tests/test_smoke_imports.py` (imports every dependency and `bgllog`).
- A public GitHub repo (Nafi approved) `bgl-log-mining` with the first commit pushed.
- `requirements.lock.txt` after a successful install.

## Steps
1. `git init` if needed; set default branch `main`.
2. Create the folder layout and copy the starter files. Keep `starter/` out of the final repo (delete it after copying, in the same commit).
3. Create the venv (see `02-environment-windows.md`), install `requirements.txt`, then `pip install -e .`.
4. Write `src/bgllog/io.py` with: `load_config(path)`, `get_logger(stage)`, `set_seed(seed)`, `ensure_dirs()`; all paths come from the config.
5. Write the smoke test and run `pytest -q`.
6. `torch` is listed in `requirements.txt`. On Nafi's machine the default PyPI wheel (CPU build on Windows) is exactly what is needed: tests, CPU dry runs, embedding extraction and the app. Do not try to get CUDA working on his machine.
7. Create the GitHub repo with `gh repo create bgl-log-mining --public --source=. --remote=origin --push`.
8. Create `docs/PROGRESS.md` entries (the file already exists as a template; mark S00).

## Definition of done
- [ ] `pytest -q` passes.
- [ ] `python -c "import bgllog, pandas, sklearn, drain3, mlxtend, prefixspan, umap, streamlit"` succeeds in the venv.
- [ ] `git remote -v` shows the GitHub repo and `git log` has the S00 commit on `main`.
- [ ] `requirements.lock.txt` committed.

## Pitfalls
- Python version: if `umap-learn` or `numba` fails to install on 3.13, recreate the venv with 3.12.
- Keep the repo path short on Windows.
- Do not commit `.venv`.

## Report hooks
None. (Environment details feed the "Metodologi" chapter, section on tools: record Python version and package versions in `reports/results.json` under `env`.)

## Note to write
`docs/notes/S00-setup.md` (Indonesian): what the repo layout is for, in five lines.
