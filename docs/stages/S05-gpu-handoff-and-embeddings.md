# S05. GPU hand-off, merge and embeddings

## Goal
Get trained LSTM and GRU weights from the teammate's RTX 5060 laptop, verify them, merge them, and extract window embeddings on CPU.

## Depends on
S04, and a human action (teammate runs training and pushes branch `gpu-run`).

## State machine

```
WAITING_FOR_TEAMMATE ──(gpu-run appears on origin)──▶ VALIDATING ──▶ MERGED ──▶ EMBEDDINGS_DONE
        │                                                  │
        └─(Nafi says: no GPU available)──▶ CPU_FALLBACK   └─(checks fail)──▶ REQUEST_RERUN (write BLOCKERS.md)
```

## While waiting
Claude Code may continue S03, and may draft report chapters for S01–S03. Do not start S06.

## Validation (when `origin/gpu-run` exists)
Run `git fetch origin`, then inspect `git diff --stat main..origin/gpu-run`. Expected changes **only** under `handoff/results/`. If anything else changed, stop and ask.

Check each of `handoff/results/lstm/` and `handoff/results/gru/` for: `best.pt`, `history.csv`, `metrics.json`, `env.json`.

| Check | Pass condition |
|---|---|
| Device really was the GPU | `env.json` shows `cuda_available: true` and a GPU name containing "5060" (or at least an NVIDIA GPU) |
| Training behaved | `history.csv`: train loss decreases overall; validation loss is finite; no NaN |
| Better than baselines | `metrics.json` test top-1 > bigram baseline and > most-frequent baseline (from S04). If not, record it honestly and continue; it is a finding, not a failure |
| Same data | `meta` hash in `env.json` equals the hash in `handoff/windows.npz` |
| File sizes sane | `best.pt` below 50 MB |

If the data or device checks fail, write `docs/BLOCKERS.md` with the exact problem and a one-line instruction to give the teammate (for example: "rerun `scripts\train_all.ps1` with the charger plugged in; CUDA was not used"), then set state `REQUEST_RERUN`.

## Merge
`git merge --no-ff origin/gpu-run -m "S05: merge GPU training results"`. Then copy the best weights to `artifacts/models/lstm/` and `artifacts/models/gru/` together with `config.json`, `history.csv`, `metrics.json` (these are the committed copies used by the app).

## Embeddings (CPU)
`scripts/s05_extract_embeddings.py` loads each model, runs batched inference with `torch.no_grad()` over `X_train`, `X_val` and `X_test` from `data/processed/windows_X.npy` (using the split indices from `windows_meta.parquet`), and saves float32 arrays `artifacts/embeddings/<model>_<split>.npy`. Use large batches (e.g. 4096) on CPU. Verify: row counts match the split sizes; no NaN; embedding dimension equals `hidden_dim`.

Also compute the **DL extra analysis** (cheap, uses only inference): per-window mean next-event loss for every window, saved as `artifacts/embeddings/<model>_window_loss.npy`; later S07 reports AUROC of this score for `has_alert`.

## CPU_FALLBACK (only if Nafi says no GPU will be available)
Run `scripts/train.py --device cpu` with `--max-train-windows` set to a size that finishes in a reasonable run (try 100,000) for both models, write results into `artifacts/models/...` directly, and state clearly in the stage note and in the report that training used a subsample on CPU.

## Definition of done
- [ ] Validation table above filled in the stage note (pass/fail per check).
- [ ] `git log` shows the merge commit; `handoff/results/` and `artifacts/models/{lstm,gru}/` exist.
- [ ] Embedding files exist for both models and all three splits with correct shapes.
- [ ] `reports/results.json` → `dl.lstm` and `dl.gru` filled (test loss, perplexity, top-1, top-5, epochs trained, training seconds, device name).
- [ ] `PROGRESS.md` updated (S05 complete or in `REQUEST_RERUN`).

## Pitfalls
- Never `git merge` before validating.
- Never force-push or reset `main`.
- The test split must remain untouched during any model selection. The choice of LSTM vs GRU for the app is made in S06 by the rule written there (validation metrics only), not here.

## Report hooks
Chapter IV.4 (DL training): loss curves (`dl_loss_curves.png`: LSTM vs GRU, train and val), a table comparing both models and the two baselines (`dl_model_comparison.csv`), and a short paragraph on the hardware used for training (the RTX 5060 laptop).

## Note to write
`docs/notes/S05-training-results.md` (Indonesian): what the loss curve means, why early stopping is used, and the LSTM vs GRU outcome in plain words.
