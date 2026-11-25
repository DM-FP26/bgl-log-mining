# S04. Training code and GPU hand-off (technical log, English)

Indonesian summary: `docs/notes/S04-model-design.md`. Numbers come from `reports/results.json` (`dl`) and `handoff/results/*` after S05.

## Goal
Write and test the LSTM/GRU training code on CPU, compute baselines, and package everything so the GPU teammate only has to clone, run one script and push.

## Steps taken (in order)
1. **Model** (`src/bgllog/models.py`): `LogRNN` = `Embedding(V, 64, padding_idx=0)` -> `LSTM|GRU(128, 2 layers, dropout 0.2, batch_first)` -> `Linear(128, V)`. `encode()` returns last-layer hidden states; `forward()` returns logits. 277,937 parameters (LSTM, V=241).
2. **Training** (`src/bgllog/train.py`): next-event loss at every position (input `X[:, :-1]`, target `X[:, 1:]`, PAD ignored); Adam lr 1e-3, grad clip 1.0, up to 20 epochs, early stopping on val loss (patience 3), seed 42. The whole train set is kept on the device (53 MB) and batched manually, so there is no DataLoader and no worker issue on Windows. `last.pt` (model, optimizer, epoch, history) is saved every epoch, `best.pt` on best val loss; `--resume` restores from `last.pt`. `--device cuda` without CUDA exits with an error; it never falls back silently. `env.json` records torch, CUDA, GPU name, arch list and the `windows_meta_hash` for S05 validation.
3. **Evaluation** (`evaluate`): loss, perplexity, top-1, top-5 (PAD targets excluded), plus `top1_on_changes` (positions where the target differs from the current event). Test metrics are written **twice** in `metrics.json`: `test` (all windows) and `test_unk_free` (S02 decision), plus `val`. The test split is evaluated once, with the best checkpoint.
4. **Embedding helper** (`src/bgllog/embed.py`): `embed_windows(model, X, pooling, ...)`, mean (default) or last-position pooling over non-PAD positions, for S05.
5. **CLI and hand-off:** `scripts/train.py` (flags `--model --device --epochs --max-train-windows --batch-size --resume --out`), `scripts/check_gpu.py` (PASS/FAIL with a fix message; on this CPU-only machine it prints FAIL and exits 1, as the spec allows), `scripts/train_all.ps1` (`-Resume`, `-BatchSize`; written for PowerShell and **not tested on Windows**, because no Windows machine was available), `handoff/README.md`, finalized `docs/GPU-HANDOFF-FRIEND.md` (owner placeholder replaced with `DM-FP26`).
6. **Baselines** (`scripts/s04_make_handoff.py`): most-frequent, bigram, and repeat-last, each on val/test, all windows and UNK-free windows, stored under `dl.baselines`.
7. **Tests** (`tests/test_models.py`, 43 tests in total pass): forward shapes (LSTM and GRU), loss ignores PAD, a training step reduces loss on a toy batch, train-then-resume produces the expected `history.csv` and metrics, CUDA-without-CUDA fails loudly, UNK-free mask, embedding shapes with PAD.
8. **CPU dry runs** on real data (`--epochs 1 --max-train-windows 2000`, both models) completed; the loss stays near chance (5.4 to 5.5, ln 241 = 5.48) after only 4 steps, as expected. A **full CPU epoch** of the LSTM (pilot, stored under `dl.cpu_pilot`) took 153 s on 4 cores and learned: val loss 0.61.

## Findings
- Baselines are strong on plain top-1 because logs repeat: test top-1 bigram 96.3% (all) / 95.4% (UNK-free), repeat-last 95.8% / 94.3%, most-frequent 0.0%. On change positions bigram gets 18.7% / 30.1% and repeat-last 0% by definition. Judge the RNN on `top1_on_changes` and loss, not only top-1.
- The most frequent train event (`generating core`, 51% of train targets) never occurs in val or test; most-frequent scores exactly 0.0 (verified, not a bug). This is a second view of the drift found in S02.
- CPU pilot (1 epoch LSTM): test UNK-free top-1 92.6% (below bigram's 95.4%) but top-1 on changes 38.0% (above bigram's 30.1%). Test over all windows has loss 5.59 because 60% of targets are UNK that were never trained on.
- A full CPU run is feasible: about 153 s per epoch, so at most 20 epochs x 2 models is roughly 100 minutes (early stopping will shorten it). The GPU hand-off is therefore a convenience, not a necessity. It stays in the plan because the team planned it that way.

## Problems hit and how they were fixed
| Problem | Fix |
|---|---|
| `--resume` with a larger `--epochs` did nothing (a run that reached its epoch cap was marked "finished") | Only an early-stopped run is final (`stopped_early`); test caught it |
| `most_frequent` baseline scored exactly 0.0 | Verified: its target never appears in val/test |
| Plain top-1 is dominated by repetition | Added `top1_on_changes` and the repeat-last baseline (not in the spec) |
| I first wrote a GPU training-time estimate into the friend's guide | Removed; it was not measured |

## Open items
- Which GitHub account is the GPU teammate? `Bima-031` has write access; `najwarjombi` has read only (checked via the API).
- The PowerShell script and the Windows+RTX 5060 path are untested until the teammate runs them.

## Reproduce
```bash
.venv/bin/python scripts/s04_make_handoff.py                    # baselines
.venv/bin/python scripts/train.py --model lstm --device cpu --epochs 1 --max-train-windows 2000 --out tmp/dryrun_lstm
.venv/bin/python -m pytest -q
```
