# Hand-off for GPU training

This folder holds `windows.npz` (the training data: only event-id windows, no labels, about 0.3 MB) and, after the GPU run, `results/` (models, curves and metrics).

**If you are the teammate with the GPU laptop, read and follow `docs/GPU-HANDOFF-FRIEND.md`.** In short: clone, make a venv with the CUDA build of PyTorch, run `scripts/check_gpu.py`, run `.\scripts\train_all.ps1`, then `git push` to branch `gpu-run`.

Contents after a run: `results/<lstm|gru>/{best.pt, history.csv, metrics.json, env.json, config.json}`. `last.pt` (optimizer state) is git-ignored on purpose.
