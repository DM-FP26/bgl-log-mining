"""S02: Drain3 templates -> event ids -> windows -> chronological split -> vocabulary -> hand-off file.

Usage (from repo root):
    python scripts/s02_preprocess.py            # full run (cached; uses data/interim/parsed.parquet from S01)
    python scripts/s02_preprocess.py --sample   # fast run on the S01 sample, separate outputs
    python scripts/s02_preprocess.py --force    # recompute templates even if cached
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import seaborn as sns  # noqa: E402

from bgllog.io import ensure_dirs, get_logger, get_path, load_config, set_seed  # noqa: E402
from bgllog.parsing import assign_event_ids, config_hash  # noqa: E402
from bgllog.windows import apply_vocab, build_vocab, build_windows, chronological_split, window_starts  # noqa: E402

MAX_HANDOFF_MB = 50
MAX_DRAIN_STATE_MB = 20


def savefig(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg["seed"])
    ensure_dirs(cfg)
    log = get_logger("s02", cfg)
    tag = "_sample" if args.sample else ""
    interim, processed = get_path(cfg, "interim_dir"), get_path(cfg, "processed_dir")
    artifacts, reports, handoff = get_path(cfg, "artifacts_dir"), get_path(cfg, "reports_dir"), get_path(cfg, "handoff_dir")
    fig_dir = reports / ("sample/figures" if args.sample else "figures")
    tab_dir = reports / ("sample/tables" if args.sample else "tables")
    fig_dir.mkdir(parents=True, exist_ok=True); tab_dir.mkdir(parents=True, exist_ok=True)
    parquet = interim / f"parsed{tag}.parquet"
    templates_csv = processed / f"templates{tag}.csv"
    drain_state = (interim / "drain3_state_sample.bin") if args.sample else (artifacts / "drain3_state.bin")
    if not parquet.exists():
        log.error("%s not found. Run scripts/s01_download_and_eda.py first.", parquet); raise SystemExit(2)

    table = pq.read_table(parquet)
    df = table.select(["line_id", "label", "is_alert", "ts", "component", "parse_ok", "content"]).to_pandas()
    n_lines = len(df)

    # ---- 1-2. templates / event ids ---------------------------------------------------------
    have_ids = "event_id" in table.column_names and templates_csv.exists()
    if have_ids and not args.force:
        log.info("Using cached event_id column and %s", templates_csv)
        df["event_id"] = table.column("event_id").to_numpy()
        tpl_df = pd.read_csv(templates_csv)
        prep_stats = json.loads((interim / f"s02_stats{tag}.json").read_text())
    else:
        ok = df["parse_ok"].to_numpy()
        ids = np.full(n_lines, -1, dtype=np.int32)  # malformed lines keep event_id = -1
        ids_ok, templates, prep_stats = assign_event_ids(
            df.loc[ok, "content"].to_numpy(), cfg, persist_path=drain_state,
            progress=lambda i, n, k: log.info("Drain3: %s/%s unique messages, %d templates so far", f"{i:,}", f"{n:,}", k))
        ids[ok] = ids_ok
        df["event_id"] = ids
        counts = pd.Series(ids[ok]).value_counts()
        alert_ratio = df.loc[ok].groupby("event_id")["is_alert"].mean()
        tpl_df = pd.DataFrame({"event_id": sorted(templates)})
        tpl_df["template"] = tpl_df["event_id"].map(templates)
        tpl_df["count"] = tpl_df["event_id"].map(counts).fillna(0).astype(int)
        tpl_df["alert_line_ratio"] = tpl_df["event_id"].map(alert_ratio).fillna(0.0).round(6)
        tpl_df.sort_values("count", ascending=False).to_csv(templates_csv, index=False)
        prep_stats["n_malformed_excluded"] = int((~ok).sum())
        (interim / f"s02_stats{tag}.json").write_text(json.dumps(prep_stats))
        # write event_id back into the parsed parquet (atomic replace)
        new = table.drop_columns(["event_id"]) if "event_id" in table.column_names else table
        new = new.append_column("event_id", pa.array(ids, type=pa.int32()))
        tmp = parquet.with_suffix(".tmp")
        pq.write_table(new, tmp, compression="zstd"); tmp.replace(parquet)
        size_mb = drain_state.stat().st_size / 1e6
        log.info("Drain3 state %.2f MB at %s", size_mb, drain_state)
        if not args.sample and size_mb > MAX_DRAIN_STATE_MB:
            log.error("drain3 state > %d MB: do not commit it. STOP and ask Nafi.", MAX_DRAIN_STATE_MB); raise SystemExit(3)
    del table
    n_templates = int(len(tpl_df))
    log.info("%s lines, %d templates", f"{n_lines:,}", n_templates)

    # ---- 3. windows over the time-ordered stream of valid lines ---------------------------
    valid = df["parse_ok"].to_numpy()
    v = df.loc[valid].reset_index(drop=True)
    size, step = cfg["windows"]["size"], cfg["windows"]["step"]
    tag_codes, tag_names = pd.factorize(v["label"].where(v["is_alert"]), sort=True)  # NaN (non-alert) -> -1
    starts = window_starts(len(v), size, step)
    n_win = len(starts)
    split = chronological_split(n_win, cfg["windows"]["split"], cfg["windows"]["gap_windows"])

    # ---- 5. vocabulary from the TRAIN split only (lines covered by train windows) ----------
    train_last_line = int(starts[np.flatnonzero(split == "train")[-1]] + size - 1)
    vocab = build_vocab(v["event_id"].to_numpy()[: train_last_line + 1], cfg["vocab"]["min_count"], cfg["vocab"]["max_size"])
    vocab_idx = apply_vocab(v["event_id"].to_numpy(), vocab)
    w = build_windows(vocab_idx, v["is_alert"].to_numpy(), tag_codes, size, step)
    X = w["X"].astype(np.int16)
    meta = pd.DataFrame({
        "window_id": np.arange(n_win, dtype=np.int32),
        "start_line": v["line_id"].to_numpy()[w["start_line"]], "end_line": v["line_id"].to_numpy()[w["end_line"]],
        "ts_start": v["ts"].to_numpy()[w["start_line"]], "ts_end": v["ts"].to_numpy()[w["end_line"]],
        "has_alert": w["has_alert"], "n_alert": w["n_alert"],
        "alert_tag": np.where(w["alert_tag_code"] >= 0, np.asarray(tag_names)[np.maximum(w["alert_tag_code"], 0)], "NONE"),
        "split": split,
    })
    meta.to_parquet(processed / f"windows_meta{tag}.parquet", index=False)
    np.save(processed / f"windows_X{tag}.npy", X)

    # ---- 6. hand-off (no labels) ----------------------------------------------------------
    vocab_size = len(vocab) + 2
    chash = config_hash(cfg)
    split_sizes = {s: int((split == s).sum()) for s in ["train", "val", "test", "gap"]}
    meta_json = json.dumps({"window_size": size, "step": step, "split_sizes": split_sizes, "vocab_size": vocab_size,
                            "config_hash": chash, "pad": 0, "unk": 1})
    vocab_json = {"pad": 0, "unk": 1, "event_to_index": {str(k): int(val) for k, val in vocab.items()}, "config_hash": chash}
    if not args.sample:
        (artifacts / "vocab.json").write_text(json.dumps(vocab_json))
        out = handoff / "windows.npz"
        np.savez_compressed(out, X_train=X[split == "train"], X_val=X[split == "val"], X_test=X[split == "test"],
                            vocab_size=np.int64(vocab_size), meta=np.array(meta_json))
        mb = out.stat().st_size / 1e6
        log.info("handoff/windows.npz = %.1f MB", mb)
        if mb > MAX_HANDOFF_MB:
            log.error("windows.npz > %d MB. STOP and ask Nafi.", MAX_HANDOFF_MB); raise SystemExit(3)
    else:
        (interim / "vocab_sample.json").write_text(json.dumps(vocab_json))

    # ---- 7. report numbers ----------------------------------------------------------------
    rows, per_split = [], {}
    for s in ["train", "val", "test"]:
        m, xs = meta[meta["split"] == s], X[split == s]
        per_split[s] = {"n_windows": int(len(m)), "alert_window_ratio": float(m["has_alert"].mean()),
                        "n_alert_windows": int(m["has_alert"].sum()), "unk_ratio": float((xs == 1).mean()),
                        "windows_with_any_unk_ratio": float((xs == 1).any(axis=1).mean()),
                        "windows_majority_unk_ratio": float(((xs == 1).mean(axis=1) > 0.5).mean()),
                        "n_windows_unk_free": int((~(xs == 1).any(axis=1)).sum()),
                        "n_alert_windows_unk_free": int((m["has_alert"].to_numpy() & ~(xs == 1).any(axis=1)).sum()),
                        "first_ts": int(m["ts_start"].min()), "last_ts": int(m["ts_end"].max())}
    summary = {
        "n_lines": n_lines, "n_lines_windowed": int(len(v)), "n_malformed_excluded": int(n_lines - len(v)),
        "n_unique_messages": prep_stats["n_unique_messages"], "n_templates": n_templates,
        "lines_changed_by_cleaning": prep_stats["lines_changed_by_cleaning"],
        "templates_covering_99pct_lines": int((tpl_df.sort_values("count", ascending=False)["count"].cumsum() < 0.99 * tpl_df["count"].sum()).sum() + 1),
        "singleton_templates": int((tpl_df["count"] == 1).sum()),
        "vocab_size_incl_pad_unk": vocab_size, "n_windows": n_win, "n_windows_with_alert": int(meta["has_alert"].sum()),
        "window_alert_ratio_all": float(meta["has_alert"].mean()), "window_size": size, "window_step": step,
        "gap_windows": cfg["windows"]["gap_windows"], "config_hash": chash, "split_sizes": split_sizes,
    }
    flat = {**summary, **{f"{s}_{k}": val for s, d in per_split.items() for k, val in d.items()}}
    flat["split_sizes"] = json.dumps(split_sizes)
    pd.DataFrame(list(flat.items()), columns=["metric", "value"]).to_csv(tab_dir / "preprocessing_summary.csv", index=False)

    # ---- figures (Indonesian) ---------------------------------------------------------------
    sns.set_theme(style="whitegrid", context="notebook")
    freq = np.sort(tpl_df["count"].to_numpy())[::-1]
    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.loglog(np.arange(1, len(freq) + 1), freq, color="#4C78A8")
    ax.set_title(f"Frekuensi template (peringkat vs jumlah baris), {n_templates} template")
    ax.set_xlabel("Peringkat template (skala log)"); ax.set_ylabel("Jumlah baris (skala log)")
    savefig(fig, fig_dir / "prep_template_frequency.png")

    comp = df.loc[valid & (df["event_id"] >= 0)].groupby("component")["event_id"].nunique()
    comp_n = df.loc[valid].groupby("component").size()
    comp = comp[comp_n.reindex(comp.index) >= 100].sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(comp.index, comp.values, color="#59A14F")
    for i, val in enumerate(comp.values):
        ax.text(i, val, str(val), ha="center", va="bottom", fontsize=9)
    ax.set_title("Jumlah template berbeda per komponen (min. 100 baris)"); ax.set_xlabel("Komponen"); ax.set_ylabel("Jumlah template")
    ax.tick_params(axis="x", rotation=45)
    savefig(fig, fig_dir / "prep_templates_per_component.png")

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    names = ["train", "val", "test"]
    vals = [100 * per_split[s]["alert_window_ratio"] for s in names]
    ax.bar(names, vals, color=["#4C78A8", "#F28E2B", "#E45756"])
    for i, s in enumerate(names):
        ax.text(i, vals[i], f"{vals[i]:.1f}%\n({per_split[s]['n_alert_windows']:,} dari {per_split[s]['n_windows']:,})", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(vals) * 1.3); ax.set_title("Persentase jendela yang mengandung alert per bagian data")
    ax.set_xlabel("Bagian data (urut waktu)"); ax.set_ylabel("% jendela dengan alert")
    savefig(fig, fig_dir / "prep_window_alert_ratio.png")

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    xk = np.arange(3)
    ax.bar(xk - 0.2, [100 * per_split[s]["unk_ratio"] for s in names], 0.4, color="#B07AA1", label="% token UNK")
    ax.bar(xk + 0.2, [100 * per_split[s]["windows_with_any_unk_ratio"] for s in names], 0.4, color="#76B7B2", label="% jendela yang memuat UNK")
    for i, s in enumerate(names):
        ax.text(i - 0.2, 100 * per_split[s]["unk_ratio"], f"{100 * per_split[s]['unk_ratio']:.1f}", ha="center", va="bottom", fontsize=9)
        ax.text(i + 0.2, 100 * per_split[s]["windows_with_any_unk_ratio"], f"{100 * per_split[s]['windows_with_any_unk_ratio']:.1f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(xk); ax.set_xticklabels(names); ax.set_ylim(0, 105); ax.legend()
    ax.set_title("Event tak dikenal (UNK) per bagian data")
    ax.set_xlabel("Bagian data (urut waktu)"); ax.set_ylabel("Persen")
    savefig(fig, fig_dir / "prep_unk_ratio.png")

    fig, ax = plt.subplots(figsize=(11, 3.6))
    n_show = 40
    for i in range(n_show):
        ax.add_patch(plt.Rectangle((i, 0), 0.9, 0.9, color="#9ecae1"))
        if i % 5 == 0:
            ax.text(i + 0.45, 0.45, str(i), ha="center", va="center", fontsize=7)
    for k, (c, lab) in enumerate([("#E45756", "Jendela 1: baris 0-19"), ("#F28E2B", "Jendela 2: baris 10-29"), ("#59A14F", "Jendela 3: baris 20-39")]):
        y = -0.5 - 0.7 * k
        ax.plot([k * step, k * step + size - 0.1], [y, y], color=c, linewidth=6, solid_capstyle="butt")
        ax.text(k * step + size + 0.3, y, lab, va="center", fontsize=9)
    ax.set_xlim(-0.5, 55); ax.set_ylim(-2.8, 1.4); ax.axis("off")
    ax.set_title(f"Jendela geser: ukuran {size} baris, langkah {step} baris (tiap kotak = 1 baris log = 1 event)")
    savefig(fig, fig_dir / "prep_window_diagram.png")

    # ---- results.json (full run only) -----------------------------------------------------
    if not args.sample:
        rp = reports / "results.json"
        res = json.loads(rp.read_text()) if rp.exists() else {}
        d = res.setdefault("dataset", {})
        d.update({"n_templates": n_templates, "n_windows": n_win, "n_windows_with_alert": summary["n_windows_with_alert"],
                  "window_size": size, "window_step": step, "split_sizes": split_sizes})
        res["preprocessing"] = {**{k: val for k, val in summary.items() if k not in ("split_sizes",)}, "per_split": per_split,
                                "drain": cfg["parsing"]["drain"], "masks": [m["name"] for m in cfg["parsing"]["masks"]]}
        rp.write_text(json.dumps(res, indent=2) + "\n")
        log.info("results.json updated (dataset, preprocessing)")
    log.info("S02 done. windows=%s split=%s", f"{n_win:,}", split_sizes)
    for s in names:
        log.info("  %s: %s windows, alert-window ratio %.2f%%, UNK %.3f%%", s, f"{per_split[s]['n_windows']:,}", 100 * per_split[s]["alert_window_ratio"], 100 * per_split[s]["unk_ratio"])


if __name__ == "__main__":
    sys.exit(main())
