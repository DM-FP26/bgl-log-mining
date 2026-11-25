import numpy as np

from bgllog.patterns import (PRE, build_control, build_prealert, collapse_repeats, eval_rule, find_burst_starts,
                             is_subsequence, mine_rules, mine_sequences, to_basket, top_items)


def toy_stream():
    """200 lines, 1 s apart. Alerts at lines 50-52 (burst 1) and 150 (burst 2); line 160-199 quiet."""
    n = 200
    ts = np.arange(n) * 1
    is_alert = np.zeros(n, bool)
    is_alert[[50, 51, 52, 150]] = True
    return ts, is_alert


def test_burst_starts_use_gap():
    ts, a = toy_stream()
    assert list(find_burst_starts(ts, a, 5)) == [50, 150]
    assert list(find_burst_starts(ts, a, 200)) == [50]            # one big burst when the gap is huge


def test_prealert_windows_exclude_burst_and_earlier_alerts():
    ts, a = toy_stream()
    starts = find_burst_starts(ts, a, 5)
    w, c = build_prealert(starts, a, 20)
    assert list(w) == [30, 130] and c["n_prealert"] == 2
    assert all(not a[s: s + 20].any() for s in w)                 # windows contain no alert line
    a2 = a.copy(); a2[40] = True                                   # an earlier alert 10 lines before burst 1
    starts2 = find_burst_starts(ts, a2, 5)
    w2, c2 = build_prealert(starts2, a2, 20)
    assert c2["dropped_contain_alert"] >= 1 and all(not a2[s: s + 20].any() for s in w2)
    w3, c3 = build_prealert(np.array([5]), a, 20)                  # not enough lines before the start
    assert len(w3) == 0 and c3["dropped_no_room"] == 1


def test_control_far_from_alerts_and_non_overlapping():
    n = 4000
    ts = np.arange(n) * 10                                          # 10 s per line
    is_alert = np.zeros(n, bool); is_alert[[500, 2500]] = True
    alert_ts = ts[is_alert]
    pre = np.array([480, 2480])
    ctrl = build_control(ts, alert_ts, 20, 600, 50, np.random.default_rng(1), exclude_ranges=pre)
    assert len(ctrl) == 50 and len(set(ctrl)) == 50
    for s in ctrl:
        assert np.abs(ts[s: s + 20][:, None] - alert_ts[None, :]).min() >= 600     # margin respected
        assert not any(s < p + 20 and p < s + 20 for p in pre)                      # no overlap with pre-alert windows
    assert (np.diff(ctrl) >= 20).all()                                              # no overlap among controls


def test_rules_find_a_perfect_predictor():
    rng = np.random.default_rng(0)
    pre = [np.array([7, 1, 2] + list(rng.integers(10, 15, 5))) for _ in range(60)]
    ctl = [np.array([1, 2] + list(rng.integers(10, 15, 6))) for _ in range(60)]
    items = top_items(pre + ctl, 20)
    basket = to_basket(pre + ctl, items, [True] * 60 + [False] * 60)
    fi, rules = mine_rules(basket, 0.1, 0.6, 1.2, 3)
    assert not rules.empty
    best = rules.iloc[0]
    assert 7 in best["antecedent_items"] and best["confidence"] == 1.0 and abs(best["lift"] - 2.0) < 1e-9
    assert all(set(c) == {PRE} for c in rules["consequents"])
    r = eval_rule((7,), basket)
    assert r["confidence"] == 1.0 and r["lift"] == 2.0 and eval_rule((99,), basket)["n_antecedent"] == 0


def test_sequences_and_subsequence_logic():
    assert collapse_repeats(np.array([1, 1, 2, 2, 2, 1])) == [1, 2, 1]
    assert is_subsequence((1, 3), [1, 2, 3]) and not is_subsequence((3, 1), [1, 2, 3])
    pre = [[5, 6, 7, 1]] * 30 + [[1, 2]] * 10
    ctl = [[1, 2]] * 40
    df = mine_sequences(pre, ctl, 0.2, 2.0, 2, 4)
    assert (5, 6, 7) in set(df.pattern) or (5, 6, 7, 1) in set(df.pattern)
    assert (df.ratio >= 2.0).all() and (df.support_pre >= 0.2).all()
