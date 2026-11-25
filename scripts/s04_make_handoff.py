"""S04: compute the non-neural baselines from handoff/windows.npz and store them in reports/results.json.

Baselines for next-event prediction (top-1 accuracy, PAD targets excluded):
  * most_frequent  : always predict the most frequent event in train
  * bigram         : previous event -> most likely next event in train (fallback: most frequent)
  * repeat_last    : predict that the next event equals the previous one
Each is reported on the full test split and on the UNK-free test windows (S02 decision).
"""
from __future__ import annotations

import json
import sys

import numpy as np

from bgllog.io import get_path, load_config, set_seed
from bgllog.train import load_windows, unk_free_mask


def top1(pred: np.ndarray, tgt: np.ndarray, prev: np.ndarray) -> dict:
    m = tgt != 0
    ch = m & (tgt != prev)                                           # next event differs from the current one
    return {"top1": float((pred[m] == tgt[m]).mean()), "top1_on_changes": float((pred[ch] == tgt[ch]).mean()),
            "n_tokens": int(m.sum()), "n_change_tokens": int(ch.sum())}


def main() -> int:
    cfg = load_config()
    set_seed(cfg["seed"])
    d = load_windows("handoff/windows.npz")
    V = d["vocab_size"]
    Xtr = d["X_train"].astype(np.int64)
    inp, tgt = Xtr[:, :-1].ravel(), Xtr[:, 1:].ravel()
    keep = tgt != 0
    inp, tgt = inp[keep], tgt[keep]
    most_freq = int(np.bincount(tgt, minlength=V).argmax())
    table = np.zeros((V, V), dtype=np.int64)
    np.add.at(table, (inp, tgt), 1)
    bigram = table.argmax(axis=1)
    bigram[table.sum(axis=1) == 0] = most_freq                      # previous event never seen as input in train

    res = {}
    for split in ["val", "test"]:
        X = d[f"X_{split}"].astype(np.int64)
        for name, subset in [("all", np.ones(len(X), bool)), ("unk_free", unk_free_mask(X))]:
            Xs = X[subset]
            i, t = Xs[:, :-1], Xs[:, 1:]
            res[f"{split}_{name}"] = {"most_frequent": top1(np.full_like(t, most_freq), t, i), "bigram": top1(bigram[i], t, i),
                                      "repeat_last": top1(i, t, i), "n_windows": int(len(Xs))}
    baselines = {"most_frequent_top1": res["test_all"]["most_frequent"]["top1"], "bigram_top1": res["test_all"]["bigram"]["top1"],
                 "repeat_last_top1": res["test_all"]["repeat_last"]["top1"],
                 "most_frequent_event_vocab_index": most_freq, "detail": res}
    rp = get_path(cfg, "reports_dir") / "results.json"
    results = json.loads(rp.read_text()) if rp.exists() else {}
    results.setdefault("dl", {})["baselines"] = baselines
    rp.write_text(json.dumps(results, indent=2) + "\n")
    for k, v in res.items():
        print(k, {n: (round(x["top1"], 4), round(x["top1_on_changes"], 4)) for n, x in v.items() if isinstance(x, dict)}, "(top1, top1_on_changes) windows", v["n_windows"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
