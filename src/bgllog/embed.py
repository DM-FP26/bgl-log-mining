"""Window embeddings: pooled hidden states of the trained RNN (device-agnostic)."""
from __future__ import annotations

import numpy as np
import torch

from bgllog.models import LogRNN


@torch.no_grad()
def embed_windows(model: LogRNN, X: np.ndarray, pooling: str = "mean", batch_size: int = 4096,
                  device: str | torch.device = "cpu") -> np.ndarray:
    """Return a float32 array ``(N, hidden)``.

    ``mean`` averages the last layer's hidden states over non-PAD positions; ``last`` takes the final
    non-PAD position. The model sees the full window (all positions), not the shifted next-event input.
    """
    if pooling not in ("mean", "last"):
        raise ValueError("pooling must be 'mean' or 'last'")
    model.eval().to(device)
    out = []
    for i in range(0, len(X), batch_size):
        xb = torch.from_numpy(np.asarray(X[i: i + batch_size], dtype=np.int64)).to(device)
        h = model.encode(xb)                                   # (B, T, H)
        mask = (xb != 0).unsqueeze(-1)                         # ignore PAD
        if pooling == "mean":
            e = (h * mask).sum(1) / mask.sum(1).clamp(min=1)
        else:
            last_idx = (xb != 0).long().cumsum(1).argmax(1)    # index of last non-PAD position
            e = h[torch.arange(len(xb), device=h.device), last_idx]
        out.append(e.float().cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, model.cfg["hidden_dim"]), dtype=np.float32)
