# S00. Setup and scaffolding (technical log, English)

Indonesian summary for presentation: `docs/notes/S00-setup.md`. This file is the internal, step-by-step version.

## Goal
A runnable repo skeleton: folders, config, installable package, Python environment, smoke tests, pushed to GitHub.

## Steps taken (in order)
1. **Planning-time inspection.** Unzipped `bgl-blueprint.zip` (Python `zipfile`, because `unzip` is not installed) and read `CLAUDE.md` and the stage specs.
2. **Chose the repo location:** `~/projects/bgl-log-mining` (outside the Obsidian vault, so the venv and 743 MB log do not get synced). Copied `CLAUDE.md`, `docs/`, `README.md`, `starter/*` into it; moved `data/raw/` (the already-downloaded BGL files) there.
3. **Placed starter files:** `.gitignore`, `.gitattributes`, `requirements*.txt`, `configs/default.yaml`, `configs/train.yaml`; created the layout from `docs/00-overview.md` section 4 with `.gitkeep` files; deleted `starter/` as the spec says.
4. **Environment** (Linux, so `uv` instead of `py -3.12`):
   ```bash
   uv venv --python 3.12 .venv
   uv pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu
   uv pip install --python .venv/bin/python -r requirements.txt
   uv pip install --python .venv/bin/python -e .
   ```
   CPU torch first because the default Linux wheel pulls multiple GB of CUDA libraries and this machine only needs CPU. Result: Python 3.12.16, torch 2.15.0+cpu, `cuda=False`.
5. **Code:** `pyproject.toml` (setuptools, `src/` layout); `src/bgllog/io.py` with `load_config`, `get_path`, `ensure_dirs`, `get_logger` (console + `logs/<stage>.log`), `set_seed` (python, numpy, torch); `tests/test_smoke_imports.py` (19 import checks + config/seed check).
6. **Verification:** `pytest -q` gave 20 passed; the import one-liner from the spec succeeded.
7. **Bookkeeping:** `requirements.lock.txt` from `uv pip freeze` (editable install line removed); `reports/results.json` got the `env` block; note and `docs/PROGRESS.md` updated.
8. **Publishing:** `git init -b main`, repo-local git identity set to the GitHub noreply address (public repo, so the real email must not appear in commits), scanned staged files for emails/tokens (none), added `*.egg-info/` to `.gitignore` after it was staged by mistake, committed, then
   `gh repo create DM-FP26/bgl-log-mining --public --source=. --remote=origin --push`.

## Decisions and deviations
| Decision | Why |
|---|---|
| Public repo instead of private | Nafi approved; student project |
| Linux + `uv` instead of Windows + `py` | Nafi's machine is Linux; code stays cross-platform (`pathlib`) |
| CPU torch from the PyTorch CPU index | No CUDA needed here; avoids a huge download |
| noreply commit email | Public repo exposes the author email |
| Added `docs/04-lecturer-additions.md`, stages S10 and S11 | New lecturer requirements (slides; break-it-on-purpose demos) |

## Gotchas
- The teammates had only read access at first (`push=false`); the GPU teammate needs write access before S05.
- The GPU guide still describes the repo as private; it was edited to say public-to-read, write access needed to push.

## Reproduce
```bash
git clone https://github.com/DM-FP26/bgl-log-mining.git && cd bgl-log-mining
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv/bin/python -r requirements.txt && uv pip install --python .venv/bin/python -e .
.venv/bin/python -m pytest -q
```
