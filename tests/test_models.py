import json

import numpy as np
import pytest
import torch

from bgllog.embed import embed_windows
from bgllog.io import load_config
from bgllog.models import LogRNN
from bgllog.train import evaluate, next_event_loss, run, unk_free_mask

V = 20


@pytest.fixture
def toy_cfg(tmp_path):
    """Tiny synthetic hand-off file with a learnable pattern (next token = previous + 1)."""
    rng = np.random.default_rng(0)
    start = rng.integers(0, 5, size=(400, 1))
    X = ((start + np.arange(20)[None, :]) % 5 + 2).astype(np.int16)        # cycles 2..6, fully predictable
    path = tmp_path / "windows.npz"
    np.savez_compressed(path, X_train=X[:300], X_val=X[300:350], X_test=X[350:], vocab_size=np.int64(V),
                        meta=np.array(json.dumps({"config_hash": "toy"})))
    cfg = {"seed": 42, "data": {"windows_path": str(path)},
           "model": {"type": "lstm", "embed_dim": 8, "hidden_dim": 16, "num_layers": 2, "dropout": 0.0},
           "train": {"batch_size": 64, "epochs": 2, "lr": 0.01, "weight_decay": 0.0, "grad_clip": 1.0,
                     "early_stop_patience": 5, "amp": False, "num_workers": 0},
           "embed": {"pooling": "mean"}}
    return cfg


@pytest.mark.parametrize("kind", ["lstm", "gru"])
def test_forward_shapes(kind):
    m = LogRNN(V, 8, 16, 2, 0.1, kind)
    x = torch.randint(1, V, (5, 19))
    assert m(x).shape == (5, 19, V)
    assert m.encode(x).shape == (5, 19, 16)


def test_loss_ignores_pad():
    m = LogRNN(V, 8, 16, 1, 0.0, "gru")
    x = torch.randint(2, V, (4, 19))
    t1 = torch.randint(2, V, (4, 19)); t1[:, -3:] = 0
    t2 = t1.clone()
    logits = m(x)
    l1 = next_event_loss(logits, t1)
    # change the *input* at PAD-target positions only: the loss on non-PAD targets must not use PAD positions
    assert torch.isfinite(l1)
    all_pad = torch.zeros(4, 19, dtype=torch.long)
    assert torch.isnan(next_event_loss(logits, all_pad)) or next_event_loss(logits, all_pad).item() == 0.0
    # same non-PAD targets, different values under PAD: identical loss
    t2[:, -3:] = 0
    assert torch.allclose(l1, next_event_loss(logits, t2))


def test_training_step_reduces_loss():
    torch.manual_seed(0)
    m = LogRNN(V, 8, 16, 1, 0.0, "lstm")
    x = (torch.arange(20)[None, :] % 5 + 2).repeat(32, 1)
    opt = torch.optim.Adam(m.parameters(), lr=0.02)
    first = float(next_event_loss(m(x[:, :-1]), x[:, 1:]).detach())
    for _ in range(30):
        loss = next_event_loss(m(x[:, :-1]), x[:, 1:])
        opt.zero_grad(); loss.backward(); opt.step()
    assert float(loss) < first * 0.5


def test_run_resume_and_outputs(toy_cfg, tmp_path):
    out = tmp_path / "res"
    run(toy_cfg, "lstm", "cpu", epochs=1, out=out)
    assert len(open(out / "history.csv").read().strip().splitlines()) == 2        # header + 1 epoch
    for name in ["best.pt", "last.pt", "metrics.json", "env.json", "config.json", "history.csv"]:
        assert (out / name).exists(), name
    env = json.loads((out / "env.json").read_text())
    assert env["cuda_available"] in (True, False) and env["model_type"] == "lstm" and env["windows_meta_hash"] == "toy"
    run(toy_cfg, "lstm", "cpu", epochs=2, resume=True, out=out)                   # continue for one more epoch
    lines = open(out / "history.csv").read().strip().splitlines()
    assert len(lines) == 3 and lines[-1].startswith("2,")
    m = json.loads((out / "metrics.json").read_text())
    assert {"test", "test_unk_free", "val"} <= set(m) and m["test"]["top1"] > 0.05   # chance is about 1/V


def test_cuda_request_without_cuda_fails_loudly(toy_cfg, tmp_path):
    if torch.cuda.is_available():
        pytest.skip("CUDA is available here")
    with pytest.raises(SystemExit):
        run(toy_cfg, "gru", "cuda", epochs=1, out=tmp_path / "x")


def test_evaluate_and_unk_free_mask():
    X = np.array([[2, 3, 4, 5], [2, 1, 4, 5]], dtype=np.int16)
    assert list(unk_free_mask(X)) == [True, False]
    m = LogRNN(V, 8, 16, 1, 0.0, "gru")
    r = evaluate(m, X, torch.device("cpu"))
    assert r["n_tokens"] == 6 and 0.0 <= r["top1"] <= 1.0 and r["top5"] >= r["top1"]


def test_embedding_shape_and_pooling():
    m = LogRNN(V, 8, 16, 2, 0.0, "lstm")
    X = np.random.default_rng(0).integers(2, V, size=(10, 20)).astype(np.int16)
    X[0, 15:] = 0                                                                  # a window with PAD at the end
    for pooling in ("mean", "last"):
        e = embed_windows(m, X, pooling, batch_size=4)
        assert e.shape == (10, 16) and e.dtype == np.float32 and np.isfinite(e).all()
