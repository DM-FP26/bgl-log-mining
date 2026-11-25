# 02. Environment (Windows)

Applies to Nafi's machine (all stages except training) and the GPU teammate's Legion (training only).
Both are Windows. Use PowerShell. Verified on 2026-11-23 unless noted.

## 1. Python and virtual environment

- Python **3.12** is the recommended default. 3.11 or 3.13 should work. If a package refuses to install, switch to 3.12 instead of patching around it.
- Create the venv in the repo root as `.venv` (already git-ignored).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m pip install --upgrade pip
pip install -r requirements.txt
```

After the first fully working install, run `pip freeze > requirements.lock.txt` and commit it. `requirements.txt` holds lower bounds only.

## 2. Packages (verified to exist on PyPI)

Latest versions seen on the PyPI index when this blueprint was written: drain3 0.9.11, mlxtend 0.25.0, prefixspan 0.5.2, umap-learn 0.6.0, scikit-learn 1.9.1, streamlit 1.67.0, plotly 7.1.0, pandas 3.1.1, pyarrow 26.0.1, torch 2.15.0, pytest 9.2.0.

Notes:

- **pandas 3.x** changed defaults (copy-on-write, string dtype). Write code that works on pandas 2.2+ and 3.x; do not rely on chained assignment.
- Use **`sklearn.cluster.HDBSCAN`** (scikit-learn ≥ 1.3). Do not install the separate `hdbscan` package (needs compilation on some setups). To our knowledge sklearn's HDBSCAN has **no `predict` for new points** (check with `hasattr(HDBSCAN(), "predict")` on the installed version); see S06 for the workaround.
- `torch` is in `requirements.txt` (CPU wheel is enough on non-GPU machines). A GPU machine installs the CUDA build first (section 3), then the rest.
- `prefixspan` and `drain3` are pure Python: slow on millions of items. Sample where the spec says so.
- UMAP uses numba: the first import and the first fit are slow because of compilation. That is normal.

## 3. PyTorch with an RTX 50-series GPU (RTX 5060 = Blackwell, compute capability sm_120)

Facts checked against PyTorch maintainers' forum answers:

- PyTorch supports all Blackwell GPUs on Linux and Windows since **2.7.0**, but only through **CUDA 12.8+ builds**. Any binary with a CUDA 12.8 (or newer) runtime works.
- `pip install torch` from default PyPI on Windows often gives a **CPU-only** build, or an old CUDA build that prints "sm_120 is not compatible". Always install from the PyTorch index.

Install command (confirm the current one with the selector at https://pytorch.org/get-started/locally/ and prefer CUDA 12.8 or newer):

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

Verify with `scripts/check_gpu.py` (spec in S04). It must print:

- torch version and `torch.version.cuda`,
- `torch.cuda.is_available()` = True,
- `torch.cuda.get_device_name(0)`,
- `torch.cuda.get_arch_list()` containing `sm_120`,
- a small CUDA tensor operation and a tiny LSTM forward/backward pass on the GPU.

If `is_available()` is False: (1) update the NVIDIA driver, (2) confirm the CUDA 12.8+ wheel was installed (`pip show torch` and the `+cu128` suffix), (3) reinstall in a fresh venv. Do not build PyTorch from source.

## 4. Windows-specific pitfalls

| Pitfall | Rule |
|---|---|
| Console encoding errors on odd characters | Open files with `encoding="utf-8", errors="replace"`; set `PYTHONUTF8=1` in docs commands if needed |
| `multiprocessing` spawn re-imports the main module | Guard entry points with `if __name__ == "__main__":`; use `num_workers=0` |
| Path separators | `pathlib.Path` only, never string concatenation |
| Line endings | `.gitattributes` has `* text=auto`; binary types are marked binary |
| Long paths | Keep the repo path short (for example `C:\dev\bgl-log-mining`) |
| Laptop throttles on battery / sleeps | See `docs/GPU-HANDOFF-FRIEND.md` |
| Execution policy blocks venv activation | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

## 5. GitHub CLI

`gh` is installed and authenticated on Nafi's machine. S00 uses it:

```powershell
gh repo create bgl-log-mining --private --source=. --remote=origin --push
# add the GPU teammate (needs his GitHub username; ask Nafi in S04):
gh api -X PUT repos/<owner>/bgl-log-mining/collaborators/<friend-username> -f permission=push
```

The collaborator call needs the teammate's GitHub username. Ask Nafi for it in S04, not earlier. The teammate then has to accept the invitation (email or github.com/notifications) before he can clone the private repo.
