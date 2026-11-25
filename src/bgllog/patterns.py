"""Pattern mining helpers (S03): bursts, pre-alert/control windows, FP-Growth rules, PrefixSpan sequences.

All functions work on the time-ordered stream of valid log lines (arrays indexed by stream position).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PRE = "PRE_ALERT"


# ---------------------------------------------------------------------------------------------
# windows
# ---------------------------------------------------------------------------------------------
def find_burst_starts(ts: np.ndarray, is_alert: np.ndarray, gap_seconds: int) -> np.ndarray:
    """Stream positions of the first alert line of every burst (alert lines at most ``gap_seconds`` apart)."""
    pos = np.flatnonzero(is_alert)
    if pos.size == 0:
        return pos
    new_burst = np.concatenate([[True], np.diff(ts[pos]) > gap_seconds])
    return pos[new_burst]


def build_prealert(starts: np.ndarray, is_alert: np.ndarray, size: int) -> tuple[np.ndarray, dict]:
    """Start positions of the ``size`` lines immediately before each burst start.

    Windows that would not fit, or that contain any alert line (from an earlier burst), are dropped so
    the pattern mining is never circular. Returns ``(window_starts, counts)``.
    """
    csum = np.concatenate([[0], np.cumsum(is_alert.astype(np.int64))])
    w = starts - size
    fits = w >= 0
    clean = np.zeros(len(starts), dtype=bool)
    clean[fits] = (csum[starts[fits]] - csum[w[fits]]) == 0
    return w[clean], {"n_bursts": int(len(starts)), "dropped_no_room": int((~fits).sum()),
                      "dropped_contain_alert": int((fits & ~clean).sum()), "n_prealert": int(clean.sum())}


def control_candidates(ts: np.ndarray, alert_ts_sorted: np.ndarray, size: int, margin_seconds: int,
                       exclude_ranges: np.ndarray | None = None) -> np.ndarray:
    """Start positions of all grid-aligned ``size``-line blocks that are >= margin from every alert line.

    Grid alignment means candidate blocks never overlap each other. Blocks touching a pre-alert window
    (``exclude_ranges``: array of start positions) are removed.
    """
    idx = np.searchsorted(alert_ts_sorted, ts)
    big = np.iinfo(np.int64).max
    left = np.where(idx > 0, ts - alert_ts_sorted[np.maximum(idx - 1, 0)], big)
    right = np.where(idx < len(alert_ts_sorted), alert_ts_sorted[np.minimum(idx, len(alert_ts_sorted) - 1)] - ts, big)
    far = np.minimum(left, right) >= margin_seconds                       # per line: far from every alert
    n_blocks = len(ts) // size
    block_ok = far[: n_blocks * size].reshape(n_blocks, size).all(axis=1)
    if exclude_ranges is not None and len(exclude_ranges):
        for s in exclude_ranges:                                          # a block overlaps [s, s+size) if it touches those lines
            for b in {s // size, (s + size - 1) // size}:
                if 0 <= b < n_blocks:
                    block_ok[b] = False
    return np.flatnonzero(block_ok) * size


def build_control(ts: np.ndarray, alert_ts_sorted: np.ndarray, size: int, margin_seconds: int, n: int,
                  rng: np.random.Generator, exclude_ranges: np.ndarray | None = None) -> np.ndarray:
    """Sample ``n`` non-overlapping control windows far (>= margin) from every alert line, uniformly."""
    cand = control_candidates(ts, alert_ts_sorted, size, margin_seconds, exclude_ranges)
    return np.sort(rng.choice(cand, size=min(n, len(cand)), replace=False))


def window_items(event_ids: np.ndarray, starts: np.ndarray, size: int) -> list[np.ndarray]:
    return [event_ids[s: s + size] for s in starts]


def to_basket(windows: list[np.ndarray], items: list[int], labels: list[bool] | None = None) -> pd.DataFrame:
    """Boolean one-hot DataFrame with one column per item, plus ``PRE_ALERT`` if labels are given."""
    item_idx = {e: i for i, e in enumerate(items)}
    mat = np.zeros((len(windows), len(items)), dtype=bool)
    for r, w in enumerate(windows):
        for e in np.unique(w):
            j = item_idx.get(int(e))
            if j is not None:
                mat[r, j] = True
    df = pd.DataFrame(mat, columns=[int(e) for e in items])
    if labels is not None:
        df[PRE] = np.asarray(labels, dtype=bool)
    return df


def top_items(windows: list[np.ndarray], max_items: int) -> list[int]:
    """The ``max_items`` event ids that occur in the most windows (document frequency)."""
    cnt: dict[int, int] = {}
    for w in windows:
        for e in np.unique(w):
            cnt[int(e)] = cnt.get(int(e), 0) + 1
    return [e for e, _ in sorted(cnt.items(), key=lambda t: (-t[1], t[0]))[:max_items]]


# ---------------------------------------------------------------------------------------------
# association rules
# ---------------------------------------------------------------------------------------------
def mine_rules(basket: pd.DataFrame, min_support: float, min_confidence: float, min_lift: float, max_len: int):
    """FP-Growth on the basket, then rules whose consequent is exactly ``{PRE_ALERT}``.

    Returns ``(frequent_itemsets, rules)``. Rule antecedents are sorted tuples of event ids.
    """
    from mlxtend.frequent_patterns import association_rules, fpgrowth

    fi = fpgrowth(basket, min_support=min_support, use_colnames=True, max_len=max_len)
    if fi.empty:
        return fi, pd.DataFrame()
    rules = association_rules(fi, num_itemsets=len(basket), metric="lift", min_threshold=min_lift)
    keep = rules["consequents"].apply(lambda s: set(s) == {PRE}) & (rules["confidence"] >= min_confidence)
    rules = rules[keep].copy()
    rules["antecedent_items"] = rules["antecedents"].apply(lambda s: tuple(sorted(int(x) for x in s)))
    rules = rules.sort_values(["lift", "confidence", "support"], ascending=False).reset_index(drop=True)
    return fi, rules


def eval_rule(antecedent: tuple[int, ...], basket: pd.DataFrame) -> dict:
    """Support, confidence and lift of ``antecedent -> PRE_ALERT`` measured on another basket."""
    m = np.ones(len(basket), dtype=bool)
    for e in antecedent:
        m &= basket[e].to_numpy() if e in basket.columns else np.zeros(len(basket), dtype=bool)
    pre = basket[PRE].to_numpy()
    n_ant = int(m.sum())
    conf = float((m & pre).sum() / n_ant) if n_ant else float("nan")
    base = float(pre.mean())
    return {"support": float((m & pre).sum() / len(basket)), "confidence": conf, "lift": conf / base if n_ant and base else float("nan"), "n_antecedent": n_ant}


# ---------------------------------------------------------------------------------------------
# sequential patterns
# ---------------------------------------------------------------------------------------------
def collapse_repeats(seq: np.ndarray) -> list[int]:
    """Drop consecutive duplicates (A A A B -> A B) so patterns describe changes, not repetition."""
    out: list[int] = []
    for e in seq:
        if not out or out[-1] != int(e):
            out.append(int(e))
    return out


def is_subsequence(pattern: tuple[int, ...], seq: list[int]) -> bool:
    it = iter(seq)
    return all(any(e == x for x in it) for e in pattern)


def sequence_support(patterns: list[tuple[int, ...]], seqs: list[list[int]]) -> np.ndarray:
    return np.array([sum(is_subsequence(p, s) for s in seqs) / max(len(seqs), 1) for p in patterns])


def mine_sequences(seqs_pre: list[list[int]], seqs_ctrl: list[list[int]], min_support: float, min_ratio: float,
                   minlen: int, maxlen: int, epsilon: float = 1e-3) -> pd.DataFrame:
    """Closed frequent subsequences of the pre-alert windows, compared with their support in control windows."""
    from prefixspan import PrefixSpan

    ps = PrefixSpan(seqs_pre)
    ps.minlen, ps.maxlen = minlen, maxlen
    found = ps.frequent(max(int(np.ceil(min_support * len(seqs_pre))), 2), closed=True)
    pats = [tuple(p) for _, p in found]
    if not pats:
        return pd.DataFrame(columns=["pattern", "support_pre", "support_ctrl", "ratio"])
    sp = sequence_support(pats, seqs_pre)
    sc = sequence_support(pats, seqs_ctrl)
    df = pd.DataFrame({"pattern": pats, "support_pre": sp, "support_ctrl": sc, "ratio": sp / np.maximum(sc, epsilon)})
    df = df[(df.support_pre >= min_support) & (df.ratio >= min_ratio)]
    return df.sort_values(["ratio", "support_pre"], ascending=False).reset_index(drop=True)
