"""Next-event sequence model (LSTM or GRU) used for window embeddings."""
from __future__ import annotations

import torch
from torch import nn


class LogRNN(nn.Module):
    """Embedding -> LSTM/GRU -> Linear. Predicts the next event at every position.

    ``forward`` returns logits ``(B, T, vocab)``; ``encode`` returns the last RNN layer's hidden
    states ``(B, T, hidden)``, which S05 pools into one window embedding.
    """

    def __init__(self, vocab_size: int, embed_dim: int = 64, hidden_dim: int = 128, num_layers: int = 2,
                 dropout: float = 0.2, rnn_type: str = "lstm") -> None:
        super().__init__()
        rnn_type = rnn_type.lower()
        if rnn_type not in ("lstm", "gru"):
            raise ValueError(f"rnn_type must be 'lstm' or 'gru', got {rnn_type!r}")
        self.cfg = dict(vocab_size=vocab_size, embed_dim=embed_dim, hidden_dim=hidden_dim,
                        num_layers=num_layers, dropout=dropout, rnn_type=rnn_type)
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        rnn_cls = nn.LSTM if rnn_type == "lstm" else nn.GRU
        self.rnn = rnn_cls(embed_dim, hidden_dim, num_layers=num_layers, batch_first=True,
                           dropout=dropout if num_layers > 1 else 0.0)
        self.out = nn.Linear(hidden_dim, vocab_size)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        h, _ = self.rnn(self.embedding(x))
        return h

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.out(self.encode(x))


def build_model(model_cfg: dict, vocab_size: int, rnn_type: str | None = None) -> LogRNN:
    return LogRNN(vocab_size, model_cfg["embed_dim"], model_cfg["hidden_dim"], model_cfg["num_layers"],
                  model_cfg["dropout"], rnn_type or model_cfg["type"])
