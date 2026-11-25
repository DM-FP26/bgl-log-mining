import numpy as np

from bgllog.io import load_config
from bgllog.parsing import assign_event_ids, clean_content, parse_line
from bgllog.windows import UNK, apply_vocab, build_vocab, build_windows, chronological_split, window_starts


def test_window_count_and_content():
    ids = np.arange(100)
    starts = window_starts(100, 20, 10)
    assert list(starts[:3]) == [0, 10, 20] and starts[-1] == 80 and len(starts) == 9
    w = build_windows(ids, np.zeros(100, bool), np.full(100, -1), 20, 10)
    assert w["X"].shape == (9, 20) and list(w["X"][1][:3]) == [10, 11, 12]


def test_label_toy_stream():
    """Hand-built stream: alerts at lines 25, 26 (tag 3) and 27 (tag 5), and line 95 (tag 7)."""
    n = 100
    is_alert = np.zeros(n, bool)
    codes = np.full(n, -1)
    for line, code in [(25, 3), (26, 3), (27, 5), (95, 7)]:
        is_alert[line] = True; codes[line] = code
    w = build_windows(np.zeros(n, dtype=int), is_alert, codes, 20, 10)
    # windows cover [0,20) [10,30) [20,40) ... [80,100)
    assert list(w["has_alert"]) == [False, True, True, False, False, False, False, False, True]
    assert list(w["n_alert"][[1, 2, 8]]) == [3, 3, 1]
    assert list(w["alert_tag_code"][[0, 1, 2, 8]]) == [-1, 3, 3, 7]  # tag 3 occurs twice, tag 5 once


def test_tie_break_first_occurrence():
    codes = np.full(20, -1); codes[2] = 9; codes[5] = 4
    is_alert = codes >= 0
    w = build_windows(np.zeros(20, dtype=int), is_alert, codes, 20, 10)
    assert w["alert_tag_code"][0] == 9  # tie 1-1, tag 9 appears first


def test_split_is_chronological_and_leak_free():
    n_lines, size, step = 5000, 20, 10
    starts = window_starts(n_lines, size, step)
    split = chronological_split(len(starts), {"train": 0.7, "val": 0.15, "test": 0.15}, gap=2)
    idx = {s: np.flatnonzero(split == s) for s in ["train", "val", "test", "gap"]}
    last_line = lambda s: starts[idx[s][-1]] + size - 1      # noqa: E731
    first_line = lambda s: starts[idx[s][0]]                  # noqa: E731
    assert last_line("train") < first_line("val") and last_line("val") < first_line("test")
    assert idx["train"].max() < idx["val"].min() < idx["val"].max() < idx["test"].min()
    assert abs(len(idx["train"]) / len(starts) - 0.7) < 0.01


def test_vocab_uses_train_only_and_maps_rest_to_unk():
    train = np.array([7] * 10 + [8] * 6 + [9] * 2)            # 9 is below min_count
    vocab = build_vocab(train, min_count=5, max_size=100)
    assert vocab == {7: 2, 8: 3}                                # 0=PAD, 1=UNK reserved, most frequent first
    out = apply_vocab(np.array([7, 8, 9, 10, 11]), vocab)       # 10, 11 never seen in train
    assert list(out) == [2, 3, UNK, UNK, UNK] and out.dtype == np.int16


def test_vocab_max_size_cap():
    train = np.repeat(np.arange(50), 10)
    assert len(build_vocab(train, 5, 12)) == 10                  # 12 minus PAD and UNK


def test_clean_content():
    assert clean_content("  a   b \x00c ") == "a b c"
    assert clean_content("") == "<EMPTY>" and clean_content("   ") == "<EMPTY>"


def test_end_to_end_smoke_2000_lines():
    """Tiny pipeline on 2,000 synthetic BGL-style lines: parse -> templates -> windows."""
    cfg = load_config()
    rng = np.random.default_rng(42)
    msgs = ["instruction cache parity error corrected", "generating core.{n}", "CE sym {n}, at 0x{h:08x}, mask 0x{h:02x}",
            "ciod: Error reading message prefix after LOGIN_MESSAGE on CioStream socket to 172.16.{n}.1:56214: Link has been severed"]
    lines = []
    for i in range(2000):
        k = int(rng.integers(0, 4)); n = int(rng.integers(0, 5000)); h = int(rng.integers(0, 2**31))
        label = "APPSEV" if k == 3 else "-"
        lines.append(f"{label} {1117838570 + i} 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.{i:06d} R02-M1-N0-C:J12-U11 RAS KERNEL INFO " + msgs[k].format(n=n, h=h))
    rows = [parse_line(x) for x in lines]
    assert all(r is not None for r in rows)
    ids, templates, stats = assign_event_ids([r["content"] for r in rows], cfg)
    assert len(ids) == 2000 and 4 <= len(templates) <= 8       # four message kinds, numbers masked
    is_alert = np.array([r["is_alert"] for r in rows])
    w = build_windows(ids, is_alert, np.where(is_alert, 0, -1), 20, 10)
    assert w["X"].shape == (199, 20)
    assert w["has_alert"].sum() > 0
