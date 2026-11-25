# S05. GPU training results

## Execution
1. Created the local `gpu-run` branch and a Python 3.11.9 virtual environment (the Windows environment spec permits Python 3.11).
2. Installed PyTorch `2.11.0+cu128`, the `requirements-train.txt` dependencies, pandas, and the editable local project package. The handoff instructions now include pandas and `pip install -e .`.
3. Ran `python scripts/check_gpu.py`. CUDA was available, the device was an NVIDIA GeForce RTX 5060 Laptop GPU, `sm_120` was listed, and the CUDA tensor plus LSTM forward/backward checks passed.
4. Ran `scripts/train_all.ps1`. Both models completed early stopping and wrote checkpoints, histories, environment metadata, and test metrics. The first invocation returned a non-zero status after writing LSTM metrics; rerunning with `-Resume` completed both models successfully.
5. Validated both `env.json` files against `handoff/windows.npz`: the recorded data hash is `8bc744b3b253`. Training and validation losses are finite; training loss decreased overall for both models. Each `best.pt` is below the 50 MB limit.
6. Ran `python scripts/s05_extract_embeddings.py` on CPU. It copied each best checkpoint and associated config/history/metrics into `artifacts/models/`, wrote the three split embeddings, per-window losses, the loss curve, and the comparison table.
7. Committed and pushed only the GPU outputs to `origin/gpu-run` in commit `1bf2457`. `git diff --name-only main..origin/gpu-run` contains only files beneath `handoff/results/`.

## Validation results

| Check | Result |
|---|---|
| GPU and architecture | Pass: RTX 5060 Laptop GPU, CUDA 12.8, `sm_120` |
| Data hash | Pass: both models record `8bc744b3b253` |
| Training behavior | Pass: train losses decrease overall; validation losses remain finite |
| Checkpoint size | Pass: LSTM 1.06 MB; GRU 0.84 MB |
| Embedding shapes | Pass: train `(332356, 128)`, val `(71219, 128)`, test `(71216, 128)` for each model |
| Window losses | Pass: 474791 finite values for each model |
| Test top-1 vs. bigram | Did not beat on all windows: LSTM 0.9577 and GRU 0.9603 vs. 0.9627 |
| UNK-free test top-1 | LSTM 0.9603; GRU 0.9602 vs. bigram 0.9537 |

The model-selection metric remains validation loss; test metrics were evaluated only after training. The lower all-window top-1 is a result, not a reason to tune on the test set.

## Reproduction
From the repository root in PowerShell, with the CUDA environment active:

```powershell
python scripts/check_gpu.py
.\scripts\train_all.ps1
python scripts/s05_extract_embeddings.py
```

For GPU setup, install the CUDA wheel first, then `pip install -r requirements-train.txt` and `pip install -e .`. `last.pt` is a local resume checkpoint and is excluded from the result commit.

## Follow-up blocker
S06 needs `data/raw/BGL.log` or `data/interim/parsed.parquet` to align the embeddings with labels and timestamps. Neither exists in this checkout, and the Zenodo hostname could not be resolved. The question and required input are recorded in `docs/BLOCKERS.md`; S06 must wait for the data or restored network access.
