"""Windowing, chronological split and vocabulary (S02). All functions are pure numpy."""
from __future__ import annotations

import numpy as np

PAD, UNK = 0, 1


def window_starts(n_lines: int, size: int, step: int) -> np.ndarray:
    """Start line of every full window; window ``i`` covers lines ``[start, start + size)``."""
    if n_lines < size:
        return np.zeros(0, dtype=np.int64)
    return np.arange(0, n_lines - size + 1, step, dtype=np.int64)


def build_windows(event_ids: np.ndarray, is_alert: np.ndarray, label_codes: np.ndarray, size: int, step: int) -> dict:
    """Slide a window over the time-ordered stream.

    ``label_codes`` holds an integer per line (``-1`` = non-alert, otherwise the alert-tag code).
    Returns ``X`` (N x size event ids) and per-window ``start_line``, ``end_line`` (inclusive),
    ``n_alert``, ``has_alert`` and ``alert_tag_code`` (most frequent tag in the window, ties broken by
    first occurrence, ``-1`` if none).
    """
    starts = window_starts(len(event_ids), size, step)
    idx = starts[:, None] + np.arange(size)[None, :]
    X = event_ids[idx]
    csum = np.concatenate([[0], np.cumsum(is_alert.astype(np.int64))])
    n_alert = csum[starts + size] - csum[starts]
    tag_code = np.full(len(starts), -1, dtype=np.int32)
    for w in np.flatnonzero(n_alert > 0):
        codes = label_codes[starts[w]: starts[w] + size]
        codes = codes[codes >= 0]
        uniq, first, counts = np.unique(codes, return_index=True, return_counts=True)
        best = np.lexsort((first, -counts))[0]  # highest count, then earliest first occurrence
        tag_code[w] = uniq[best]
    return {"X": X, "start_line": starts, "end_line": starts + size - 1, "n_alert": n_alert.astype(np.int32),
            "has_alert": n_alert > 0, "alert_tag_code": tag_code}


def chronological_split(n_windows: int, fractions: dict, gap: int) -> np.ndarray:
    """Label each window ``train`` / ``val`` / ``test`` / ``gap`` by position in time.

    ``gap`` windows are discarded between consecutive splits. With window step <= size/2 and gap >= 2
    no line is shared across splits.
    """
    n_train = int(n_windows * fractions["train"])
    n_val = int(n_windows * fractions["val"])
    split = np.full(n_windows, "test", dtype=object)
    split[:n_train] = "train"
    split[n_train: n_train + gap] = "gap"
    v0 = n_train + gap
    split[v0: v0 + n_val] = "val"
    split[v0 + n_val: v0 + n_val + gap] = "gap"
    return split.astype(str)


def build_vocab(train_events: np.ndarray, min_count: int, max_size: int) -> dict[int, int]:
    """Map event_id -> vocab index (0=PAD, 1=UNK reserved), using the TRAIN split only.

    Events seen fewer than ``min_count`` times are left out (they become UNK). Most frequent first;
    ties broken by event_id so the result is deterministic.
    """
    ids, counts = np.unique(train_events, return_counts=True)
    keep = [(int(i), int(c)) for i, c in zip(ids, counts) if c >= min_count and i >= 0]
    keep.sort(key=lambda t: (-t[1], t[0]))
    keep = keep[: max_size - 2]
    return {eid: rank + 2 for rank, (eid, _) in enumerate(keep)}


def apply_vocab(event_ids: np.ndarray, vocab: dict[int, int]) -> np.ndarray:
    """Replace event ids by vocab indices; unknown events become UNK. Returns int16."""
    out = np.full(event_ids.shape, UNK, dtype=np.int16)
    if not vocab:
        return out
    keys = np.array(sorted(vocab), dtype=np.int64)
    vals = np.array([vocab[int(k)] for k in keys], dtype=np.int64)
    pos = np.minimum(np.searchsorted(keys, event_ids), len(keys) - 1)
    hit = keys[pos] == event_ids
    out[hit] = vals[pos[hit]]
    return out
