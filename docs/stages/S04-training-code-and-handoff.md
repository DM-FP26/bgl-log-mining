# S04. Training code and hand-off package

## Goal
Write and test the LSTM/GRU training code on CPU, then prepare everything the GPU teammate needs so that his part is: clone, run one command, push.

## Depends on
S02.

## Inputs
`handoff/windows.npz`, `configs/train.yaml`, `docs/GPU-HANDOFF-FRIEND.md` (template).

## Model definition (fixed)
- **Task:** next-event prediction at every position (language-model style). Input is `X[:, :-1]`, target is `X[:, 1:]`. PAD (index 0) is ignored in the loss.
- **Architecture:** `Embedding(vocab_size, embed_dim, padding_idx=0)` → `LSTM` or `GRU` (`num_layers`, `dropout`, `batch_first=True`) → `Linear(hidden_dim, vocab_size)`.
- **Defaults** (`configs/train.yaml`): embed 64, hidden 128, 2 layers, dropout 0.2, batch size 512, Adam lr 1e-3, grad-clip 1.0, up to 20 epochs, early stopping on validation loss with patience 3, seed 42, `amp: false`.
- **Embedding of a window** (used in S05): pooled hidden states of the last RNN layer; `embed.pooling` is `mean` by default (`last` allowed as an ablation).

## Outputs
- `src/bgllog/models.py` (`LogRNN`), `src/bgllog/train.py` (training loop, checkpoints, resume), `src/bgllog/embed.py` (batch inference, device-agnostic).
- `scripts/train.py` (CLI), `scripts/check_gpu.py`, `scripts/train_all.ps1`.
- `handoff/README.md` pointing to `docs/GPU-HANDOFF-FRIEND.md` (final version with the real repo URL and teammate's username).
- `tests/test_models.py`.
- Baselines computed on CPU from `handoff/windows.npz` and saved to `reports/results.json` → `dl.baselines`: **most-frequent-next-event** and **bigram** (previous event → most likely next event) top-1 accuracy on the test split. The RNN must beat both, or the report says it does not.
- A message for Nafi to send to the teammate (print it in chat at the end of the stage).

## `scripts/train.py` contract
```
python scripts/train.py --config configs/train.yaml --model lstm|gru
        [--device auto|cpu|cuda] [--epochs N] [--max-train-windows N] [--resume] [--out handoff/results/<model>]
```
It must:
1. Pick the device (`auto` = cuda if available else cpu) and **print loudly** which device and GPU name are used.
2. Fix seeds; log torch, CUDA and GPU info to `<out>/env.json`, including `cuda_available`, `gpu_name`, `windows_meta_hash` (the config hash stored in `handoff/windows.npz`), the model type and the full resolved config. S05 validates these fields.
3. Train on `X_train`, validate on `X_val` every epoch, save `last.pt` every epoch (model + optimizer + epoch + best val loss) and `best.pt` for the best validation loss.
4. Write `history.csv` (`epoch, train_loss, val_loss, val_top1, val_top5, seconds`).
5. After training, evaluate **once** on `X_test`: loss, perplexity, top-1, top-5 (PAD excluded). Save `metrics.json`.
6. Support `--resume` (continue from `last.pt` if it exists).
7. Use `num_workers=0`, `pin_memory=True` only when using CUDA.
8. Exit non-zero on failure; never silently fall back from CUDA to CPU when `--device cuda` was requested.

## `scripts/check_gpu.py` contract
Prints torch version, CUDA version, `is_available`, device name, `get_arch_list()`, whether `sm_120` is listed, runs a tiny LSTM forward/backward on the GPU, and ends with `GPU CHECK: PASS` or `GPU CHECK: FAIL` plus a one-line reason and the fix from `02-environment-windows.md`.

## `scripts/train_all.ps1`
Parameters: `-Resume` (switch, passes `--resume`) and `-BatchSize <int>` (optional, overrides the config batch size). Activates the venv if present, runs `check_gpu.py`, aborts on FAIL, then runs `train.py --device cuda` for `lstm` then `gru` with output to `handoff/results/lstm` and `handoff/results/gru`, then prints which files to commit (`git add handoff/results`). Must work when launched from the repo root in PowerShell. `docs/GPU-HANDOFF-FRIEND.md` refers to these two parameters, so keep the names exactly.

## Steps
1. PyTorch (CPU build) is already installed from `requirements.txt`. Implement the code above.
2. Unit tests: model forward shapes; loss ignores PAD; one training step reduces loss on a toy batch; resume works (train 1 epoch, resume 1 more).
3. CPU dry run on the real handoff data with tiny settings, for both models:
   `python scripts/train.py --config configs/train.yaml --model lstm --device cpu --epochs 1 --max-train-windows 2000 --out tmp/dryrun_lstm`
   (use `tmp/`, which is git-ignored). Confirm that metrics are produced and that top-1 beats chance.
4. Compute and store the two baselines.
5. Finalize `docs/GPU-HANDOFF-FRIEND.md`: replace the `<...>` placeholders with the real values. **Ask Nafi for the teammate's GitHub username**, then add him as a collaborator (see `02-environment-windows.md` §5).
6. Commit and push `main`. Confirm that a fresh clone into a temp folder contains `handoff/windows.npz`, `configs/train.yaml`, `scripts/*`, `requirements-train.txt` (use `git clone` to a temp path as a test).
7. Print the "message for the teammate" (the repo URL and the three-line instruction). Mark S04 done in `PROGRESS.md`, set S05 to *waiting*.

## Definition of done
- [ ] `pytest -q` passes (including model tests).
- [ ] CPU dry run completed for both models; metrics beat the most-frequent-event baseline.
- [ ] `check_gpu.py` runs on Nafi's machine without crashing (it may print FAIL there if no NVIDIA GPU; that is acceptable, the script's message must be clear).
- [ ] Fresh-clone test passed.
- [ ] Teammate added as collaborator (or Nafi explicitly postponed it).

## Pitfalls
- Do not make the teammate install the whole `requirements.txt`; training needs only `requirements-train.txt` + torch.
- Never commit `last.pt` optimizer states over a few MB; commit `best.pt`, `history.csv`, `metrics.json`, `env.json`. Add `handoff/results/**/last.pt` to `.gitignore`.
- Mixed precision is off by default. Do not turn it on without a reason.
- Do not hide device fallbacks.

## Report hooks
Chapter III.4 (model design diagram: Embedding → RNN → Linear, next-event task) and chapter II (LSTM/GRU theory).

## Note to write
`docs/notes/S04-model-design.md` (Indonesian): what "predict the next event" means and why it makes a good fingerprint for a window.
