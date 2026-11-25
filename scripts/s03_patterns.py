"""S03: pattern mining on pre-alert vs control windows (FP-Growth rules, PrefixSpan sequences).

Usage (from repo root):
    python scripts/s03_patterns.py            # full run
    python scripts/s03_patterns.py --sample   # on the S01/S02 sample, separate outputs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import seaborn as sns  # noqa: E402

from bgllog.io import ensure_dirs, get_logger, get_path, load_config, set_seed  # noqa: E402
from bgllog.patterns import (PRE, build_control, build_prealert, collapse_repeats, control_candidates, eval_rule,  # noqa: E402
                             find_burst_starts, mine_rules, mine_sequences, to_basket, top_items)

ERROR_LEVELS = {"FATAL", "SEVERE", "ERROR", "FAILURE"}


def short(text: str, n: int = 48) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


_PLACEHOLDER = re.compile(r"<[A-Z*]+>|\bat\b")


def nick(text: str, words: int = 5) -> str:
    """Short readable event name: drop placeholders (<NUM>, <HEX>, <*>) and keep the first few words."""
    w = [x for x in _PLACEHOLDER.sub(" ", text).replace(",", " ").split() if x]
    return " ".join(w[:words]) or text[:30]


def savefig(fig, path) -> None:
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    pc = cfg["patterns"]
    size = cfg["windows"]["size"]
    set_seed(cfg["seed"])
    ensure_dirs(cfg)
    log = get_logger("s03", cfg)
    tag = "_sample" if args.sample else ""
    interim, processed = get_path(cfg, "interim_dir"), get_path(cfg, "processed_dir")
    artifacts, reports = get_path(cfg, "artifacts_dir"), get_path(cfg, "reports_dir")
    fig_dir = reports / ("sample/figures" if args.sample else "figures")
    tab_dir = reports / ("sample/tables" if args.sample else "tables")
    art_dir = (interim / "patterns_sample") if args.sample else (artifacts / "patterns")
    for d in (fig_dir, tab_dir, art_dir):
        d.mkdir(parents=True, exist_ok=True)

    # ---- stream -------------------------------------------------------------------------
    df = pq.read_table(interim / f"parsed{tag}.parquet", columns=["line_id", "ts", "is_alert", "label", "level", "event_id", "parse_ok"]).to_pandas()
    df = df[df["parse_ok"]].reset_index(drop=True)
    ts, is_alert, ev = df["ts"].to_numpy(), df["is_alert"].to_numpy(), df["event_id"].to_numpy()
    line_id, labels = df["line_id"].to_numpy(), df["label"].to_numpy()
    tpl = pd.read_csv(processed / f"templates{tag}.csv").set_index("event_id")
    tpl_text = tpl["template"].to_dict()
    err_ratio = df.assign(err=df["level"].isin(ERROR_LEVELS)).groupby("event_id")["err"].mean().to_dict()

    # ---- 1. P and C -----------------------------------------------------------------------
    burst_starts = find_burst_starts(ts, is_alert, pc["burst_gap_seconds"])
    p_starts, p_counts = build_prealert(burst_starts, is_alert, size)
    keep_bursts = p_starts + size                                          # stream position of the burst start behind each P window
    cap = pc["max_windows_per_class"]
    if len(p_starts) > cap:
        sel = np.sort(np.random.default_rng(cfg["seed"]).choice(len(p_starts), cap, replace=False))
        p_starts, keep_bursts = p_starts[sel], keep_bursts[sel]
    n_p = len(p_starts)
    alert_ts = np.sort(ts[is_alert])
    margin = pc["control_margin_minutes"] * 60

    def draw_control(seed: int) -> np.ndarray:
        return build_control(ts, alert_ts, size, margin, n_p, np.random.default_rng(seed), exclude_ranges=p_starts)

    c_starts = draw_control(cfg["seed"])
    overlap = int(sum(1 for s in c_starts if np.any((s < p_starts + size) & (p_starts < s + size))))
    log.info("bursts=%d, pre-alert windows=%d (dropped: %d contain earlier alerts, %d no room), control=%d, P/C overlaps=%d",
             p_counts["n_bursts"], n_p, p_counts["dropped_contain_alert"], p_counts["dropped_no_room"], len(c_starts), overlap)
    assert overlap == 0

    win_p = [ev[s: s + size] for s in p_starts]
    win_c = [ev[s: s + size] for s in c_starts]
    p_tag = labels[keep_bursts]                                            # alert tag of each burst start
    month = lambda arr_ts: pd.to_datetime(arr_ts, unit="s").to_period("M").astype(str)  # noqa: E731
    time_comp = {"pre_alert_by_month": month(ts[p_starts]).value_counts().sort_index().to_dict(),
                 "control_by_month": month(ts[c_starts]).value_counts().sort_index().to_dict(),
                 "pre_alert_by_tag": pd.Series(p_tag).value_counts().to_dict()}

    # ---- 2-3. itemsets and rules --------------------------------------------------------------
    items = top_items(win_p + win_c, pc["max_items"])
    basket = to_basket(win_p + win_c, items, [True] * n_p + [False] * len(c_starts))
    steps, ms, mc = [], pc["min_support"], pc["min_confidence"]
    while True:
        fi, rules = mine_rules(basket, ms, mc, pc["min_lift"], pc["max_len"])
        steps.append({"min_support": ms, "min_confidence": mc, "n_itemsets": int(len(fi)), "n_rules": int(len(rules))})
        if len(rules) > 0 or ms <= 0.005:
            break
        ms, mc = ms / 2, max(mc - 0.05, 0.5)                                # documented, never silent
        log.warning("no rules; lowering thresholds to min_support=%.4f min_confidence=%.2f", ms, mc)
    log.info("itemsets=%d rules=%d (thresholds %s)", len(fi), len(rules), steps[-1])

    def text_of(itemset) -> str:
        return " | ".join(tpl_text.get(int(i), str(i)) if i != PRE else PRE for i in sorted(itemset, key=str))

    fi_out = fi.assign(length=fi["itemsets"].apply(len), templates=fi["itemsets"].apply(text_of),
                       itemset=fi["itemsets"].apply(lambda s: " ".join(str(i) for i in sorted(s, key=str)))).drop(columns="itemsets")
    fi_out.sort_values("support", ascending=False).to_csv(tab_dir / "frequent_itemsets.csv", index=False)
    if not rules.empty:
        rules["antecedent_templates"] = rules["antecedent_items"].apply(lambda t: " | ".join(tpl_text.get(i, str(i)) for i in t))
        rules["antecedent_error_level_ratio"] = rules["antecedent_items"].apply(lambda t: float(np.mean([err_ratio.get(i, 0.0) for i in t])))
        rules["antecedent_alert_line_ratio"] = rules["antecedent_items"].apply(lambda t: float(np.mean([tpl["alert_line_ratio"].get(i, 0.0) for i in t])))
        cols = ["antecedent_items", "antecedent_templates", "support", "confidence", "lift", "leverage", "antecedent support",
                "antecedent_error_level_ratio", "antecedent_alert_line_ratio"]
        rules_out = rules[cols].rename(columns={"antecedent_items": "antecedent_event_ids"})
        rules_out["antecedent_event_ids"] = rules_out["antecedent_event_ids"].apply(lambda t: " ".join(map(str, t)))
        rules_out.to_csv(tab_dir / "association_rules.csv", index=False)

    # ---- 4. sequential patterns --------------------------------------------------------------
    rng = np.random.default_rng(cfg["seed"])
    sub = lambda wins: [wins[i] for i in rng.choice(len(wins), min(pc["seq_sample"], len(wins)), replace=False)]  # noqa: E731
    seq_p = [collapse_repeats(w) for w in sub(win_p)]
    seq_c = [collapse_repeats(w) for w in sub(win_c)]
    seqs = mine_sequences(seq_p, seq_c, pc["seq_min_support"], pc["seq_min_ratio"], pc["seq_minlen"], pc["seq_maxlen"])
    seq_steps = [{"seq_min_support": pc["seq_min_support"], "n_patterns": int(len(seqs))}]
    sup = pc["seq_min_support"]
    while seqs.empty and sup > 0.01:
        sup /= 2
        seqs = mine_sequences(seq_p, seq_c, sup, pc["seq_min_ratio"], pc["seq_minlen"], pc["seq_maxlen"])
        seq_steps.append({"seq_min_support": sup, "n_patterns": int(len(seqs))}); log.warning("no sequential patterns; lowering support to %.4f", sup)
    if not seqs.empty:
        seqs["templates"] = seqs["pattern"].apply(lambda p: " -> ".join(tpl_text.get(e, str(e)) for e in p))
        seqs["event_ids"] = seqs["pattern"].apply(lambda p: " ".join(map(str, p)))
        seqs["length"] = seqs["pattern"].apply(len)
        seqs_out = seqs.drop(columns="pattern")
        seqs_out.to_csv(tab_dir / "sequential_patterns_prealert.csv", index=False)
    log.info("sequential patterns: %d", len(seqs))

    # ---- 6. honest checks ----------------------------------------------------------------------
    checks: dict = {"threshold_steps_rules": steps, "threshold_steps_sequences": seq_steps}
    if not rules.empty:
        top20 = rules.head(20)
        checks["share_top_rules_with_error_level_template"] = float((top20["antecedent_error_level_ratio"] >= 0.5).mean())
        checks["share_top_rules_with_alert_labelled_template"] = float((top20["antecedent_alert_line_ratio"] >= 0.5).mean())
        # stability: another random control sample (seed 43)
        c2 = draw_control(pc["stability_seed"])
        basket2 = to_basket(win_p + [ev[s: s + size] for s in c2], items, [True] * n_p + [False] * len(c2))
        _, rules2 = mine_rules(basket2, ms, mc, pc["min_lift"], pc["max_len"])
        top20_ids = {t for t in top20["antecedent_items"]}
        again = {t for t in rules2.head(20)["antecedent_items"]} if not rules2.empty else set()
        in_any = {t for t in rules2["antecedent_items"]} if not rules2.empty else set()
        checks["stability_seed43"] = {"top20_in_top20_again": len(top20_ids & again), "top20_found_anywhere_again": len(top20_ids & in_any),
                                      "n_rules_seed43": int(len(rules2))}
        # temporal hold-out: mine on the first (1 - f) of windows in time, evaluate the top rules on the last f
        cut = np.quantile(np.concatenate([ts[p_starts], ts[c_starts]]), 1 - pc["holdout_fraction"])
        all_starts = np.concatenate([p_starts, c_starts]); lab = np.array([True] * n_p + [False] * len(c_starts))
        early, late = ts[all_starts] < cut, ts[all_starts] >= cut
        bk = to_basket(win_p + win_c, items, lab)
        _, rules_e = mine_rules(bk[early].reset_index(drop=True), ms, mc, pc["min_lift"], pc["max_len"])
        if not rules_e.empty:
            late_bk = bk[late].reset_index(drop=True)
            ev_rows = [eval_rule(t, late_bk) for t in rules_e.head(20)["antecedent_items"]]
            lifts = np.array([r["lift"] for r in ev_rows])
            checks["temporal_holdout"] = {"n_rules_mined_early": int(len(rules_e)), "late_pre_alert_windows": int(late_bk[PRE].sum()),
                                          "late_control_windows": int((~late_bk[PRE]).sum()), "top20_median_lift_late": float(np.nanmedian(lifts)),
                                          "top20_share_lift_ge_min_lift_late": float(np.nanmean(lifts >= pc["min_lift"]))}
        # time-matched control: same months for P and C, balanced per month (guards against a time confound)
        cand = control_candidates(ts, alert_ts, size, margin, p_starts)
        m_c, m_p = pd.Series(month(ts[cand])).to_numpy(), pd.Series(month(ts[p_starts])).to_numpy()
        rng_m = np.random.default_rng(cfg["seed"])
        pm, cm = [], []
        for m in sorted(set(m_p) & set(m_c)):
            ip, ic = np.flatnonzero(m_p == m), np.flatnonzero(m_c == m)
            k = min(len(ip), len(ic))
            pm += list(p_starts[rng_m.choice(ip, k, replace=False)]); cm += list(cand[rng_m.choice(ic, k, replace=False)])
        if pm:
            bm = to_basket([ev[s: s + size] for s in pm] + [ev[s: s + size] for s in cm], items, [True] * len(pm) + [False] * len(cm))
            ev_m = [eval_rule(tt, bm) for tt in top20["antecedent_items"]]
            lm = np.array([r["lift"] for r in ev_m])
            _, rules_m = mine_rules(bm, max(ms, 0.02), mc, pc["min_lift"], pc["max_len"])
            again_m = {tt for tt in rules_m["antecedent_items"]} if not rules_m.empty else set()
            checks["time_matched_control"] = {"months_used": sorted(set(m_p) & set(m_c)), "n_pre_alert": len(pm), "n_control": len(cm),
                                              "top20_median_lift": float(np.nanmedian(lm)), "top20_share_lift_ge_min_lift": float(np.nanmean(lm >= pc["min_lift"])),
                                              "n_rules_remined": int(len(rules_m)), "top20_found_in_remined": len(top20_ids & again_m)}
    checks["time_composition"] = time_comp
    checks["control_baseline_note"] = "P and C are balanced, so PRE_ALERT support is 0.5 and lift = confidence / 0.5 (max 2.0)."

    # ---- examples ---------------------------------------------------------------------------------
    ex_rows = []
    lab_start = {int(p): i for i, p in enumerate(p_starts)}
    def window_story(s: int) -> str:
        return " > ".join(short(tpl_text.get(e, str(e)), 38) for e in collapse_repeats(ev[s: s + size])[:8])
    if not rules.empty:
        for _, r in rules.head(4).iterrows():
            for k, s in enumerate(p_starts):
                if set(r["antecedent_items"]) <= set(ev[s: s + size].tolist()):
                    b = keep_bursts[k]
                    ex_rows.append({"kind": "rule", "pattern": r["antecedent_templates"], "support": r["support"], "confidence": r["confidence"], "lift": r["lift"],
                                    "example_window_start_line": int(line_id[s]), "example_window_events": window_story(s),
                                    "followed_by_alert_tag": labels[b], "followed_by_alert_message": tpl_text.get(int(ev[b]), "")})
                    break
    if not seqs.empty:
        from bgllog.patterns import is_subsequence
        for _, r in seqs.head(2).iterrows():
            for k, s in enumerate(p_starts):
                if is_subsequence(r["pattern"], collapse_repeats(ev[s: s + size])):
                    b = keep_bursts[k]
                    ex_rows.append({"kind": "sequence", "pattern": r["templates"], "support": r["support_pre"], "confidence": r["ratio"], "lift": np.nan,
                                    "example_window_start_line": int(line_id[s]), "example_window_events": window_story(s),
                                    "followed_by_alert_tag": labels[b], "followed_by_alert_message": tpl_text.get(int(ev[b]), "")})
                    break
    pd.DataFrame(ex_rows).to_csv(tab_dir / "pattern_examples.csv", index=False)

    # ---- app copies -------------------------------------------------------------------------------
    if not rules.empty:
        rules_out.head(200).to_csv(art_dir / "rules.csv", index=False)
    if not seqs.empty:
        seqs_out.head(200).to_csv(art_dir / "seq_patterns.csv", index=False)

    # ---- figures (Indonesian) -------------------------------------------------------------------------
    sns.set_theme(style="whitegrid", context="notebook")
    if not rules.empty:
        top = rules.head(15)[::-1]
        fig, ax = plt.subplots(figsize=(11, 7))
        labels_ = [textwrap.fill(" + ".join(nick(tpl_text.get(i, str(i)), 4) for i in tt), 48) for tt in top["antecedent_items"]]
        cover = 100 * top["support"] / 0.5                                   # share of pre-alert windows containing the pattern
        ax.barh(range(len(top)), cover, color="#E45756")
        ax.set_yticks(range(len(top))); ax.set_yticklabels(labels_, fontsize=8)
        for i, (cv, cf) in enumerate(zip(cover, top["confidence"])):
            ax.text(cv, i, f"  confidence {100 * cf:.0f}%", va="center", fontsize=8)
        ax.set_xlim(0, cover.max() * 1.35)
        ax.set_title("15 aturan teratas sebelum alert")
        ax.set_xlabel("% jendela pra-alert yang memuat kombinasi"); ax.set_ylabel("Kombinasi event")
        savefig(fig, fig_dir / "pat_top_rules_lift.png")

        fig, ax = plt.subplots(figsize=(7.5, 5))
        sc = ax.scatter(rules["support"], rules["confidence"], c=rules["lift"], s=14 + 14 * rules["antecedent_items"].apply(len), cmap="viridis", alpha=0.7)
        fig.colorbar(sc, label="Lift")
        ax.set_title("Support vs confidence semua aturan (ukuran titik = jumlah event)"); ax.set_xlabel("Support"); ax.set_ylabel("Confidence")
        savefig(fig, fig_dir / "pat_support_confidence.png")
    if not seqs.empty:
        top = seqs.head(12)[::-1]
        fig, ax = plt.subplots(figsize=(11, 6.5))
        y = np.arange(len(top))
        ax.barh(y + 0.2, top["support_pre"], 0.4, color="#E45756", label="Sebelum alert")
        ax.barh(y - 0.2, top["support_ctrl"], 0.4, color="#4C78A8", label="Kontrol")
        ax.set_yticks(y); ax.set_yticklabels([textwrap.fill(" > ".join(nick(tpl_text.get(e, str(e)), 3) for e in pat), 50) for pat in top["pattern"]], fontsize=7)
        ax.set_title("12 pola berurutan teratas"); ax.set_xlabel("Proporsi jendela yang memuat pola"); ax.legend()
        savefig(fig, fig_dir / "pat_top_seq_patterns.png")

    # ---- results.json (full run only) ------------------------------------------------------------------
    if not args.sample:
        rp = reports / "results.json"
        res = json.loads(rp.read_text()) if rp.exists() else {}
        top_rules = [] if rules.empty else [{"antecedent": r["antecedent_templates"], "support": float(r["support"]), "confidence": float(r["confidence"]), "lift": float(r["lift"])}
                                            for _, r in rules.head(10).iterrows()]
        top_seq = [] if seqs.empty else [{"pattern": r["templates"], "support_pre": float(r["support_pre"]), "support_ctrl": float(r["support_ctrl"]), "ratio": float(r["ratio"])}
                                         for _, r in seqs.head(10).iterrows()]
        res["patterns"] = {"n_bursts": p_counts["n_bursts"], "n_prealert_windows": n_p, "n_control_windows": int(len(c_starts)), "prealert_counts": p_counts,
                           "items_used": len(items), "thresholds_used": {"min_support": ms, "min_confidence": mc, "min_lift": pc["min_lift"], "max_len": pc["max_len"]},
                           "n_itemsets": int(len(fi)), "n_rules": int(len(rules)), "n_sequential_patterns": int(len(seqs)),
                           "top_rules": top_rules, "top_seq_patterns": top_seq, "checks": checks}
        rp.write_text(json.dumps(res, indent=2, default=str) + "\n")
        log.info("results.json updated (patterns)")
    log.info("S03 done. checks: %s", {k: v for k, v in checks.items() if k not in ("time_composition", "threshold_steps_rules", "threshold_steps_sequences", "control_baseline_note")})


if __name__ == "__main__":
    sys.exit(main())
