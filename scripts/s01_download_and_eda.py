"""S01: download BGL, parse every line, audit the mess, write EDA tables and figures.

Usage (from repo root):
    python scripts/s01_download_and_eda.py            # full run (idempotent, cached)
    python scripts/s01_download_and_eda.py --sample   # fast run on a slice, separate output dirs
    python scripts/s01_download_and_eda.py --force    # recompute everything

S01 only MEASURES. It does not clean anything (cleaning decisions belong to S02).
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import seaborn as sns  # noqa: E402

from bgllog.io import ensure_dirs, get_logger, get_path, load_config, set_seed  # noqa: E402
from bgllog.parsing import parse_line, read_bgl  # noqa: E402

SCHEMA = pa.schema([
    ("line_id", pa.int32()), ("label", pa.string()), ("is_alert", pa.bool_()), ("ts", pa.int64()),
    ("date", pa.string()), ("node", pa.string()), ("time_full", pa.string()), ("type", pa.string()),
    ("component", pa.string()), ("level", pa.string()), ("content", pa.string()),
    ("parse_ok", pa.bool_()), ("has_node_repeat", pa.bool_()),
])
LONG_MSG = 1000
GAP_SECONDS = 3600
MIN_TAG_LINES = 100


# --------------------------------------------------------------------------------------
# 1. download
# --------------------------------------------------------------------------------------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ensure_raw(cfg: dict, log, force: bool) -> tuple[Path, Path]:
    import requests

    raw_dir = get_path(cfg, "raw_dir")
    raw_dir.mkdir(parents=True, exist_ok=True)
    zip_path, log_path = raw_dir / cfg["data"]["zip_name"], raw_dir / cfg["data"]["log_name"]
    if log_path.exists() and not force:
        log.info("BGL.log already present (%.1f MB), skipping download", log_path.stat().st_size / 1e6)
        return zip_path, log_path
    if not zip_path.exists() or force:
        log.info("Downloading %s", cfg["data"]["zenodo_url"])
        try:
            with requests.get(cfg["data"]["zenodo_url"], stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(zip_path, "wb") as fh:
                    for block in r.iter_content(1 << 20):
                        fh.write(block)
        except Exception as exc:  # stop-and-ask rule: download blocked
            log.error("Download failed: %s. Write the question to docs/BLOCKERS.md and ask Nafi.", exc)
            raise SystemExit(2)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(raw_dir)
    return zip_path, log_path


# --------------------------------------------------------------------------------------
# 2. streaming parse + audit
# --------------------------------------------------------------------------------------
def parse_and_audit(log_path: Path, out_parquet: Path, rejects_path: Path, cfg: dict, log,
                    limit: int | None, offset: int) -> dict:
    chunk_rows = cfg["parsing"]["chunk_rows"]
    st = dict(n_lines=0, malformed=0, empty_content=0, replaced_char_lines=0, non_ascii_lines=0,
              long_messages=0, duplicate_lines=0, ts_out_of_order=0, missing_node_repeat=0,
              ts_vs_time_full_other_offset=0)
    seen: set[int] = set()
    offsets: Counter = Counter()
    gaps: list[dict] = []
    rejects: list[str] = []
    prev_ts: int | None = None
    rows: list[dict] = []
    writer = pq.ParquetWriter(out_parquet, SCHEMA, compression="zstd")

    def flush() -> None:
        if rows:
            writer.write_table(pa.Table.from_pylist(rows, schema=SCHEMA))
            rows.clear()

    for line_id, raw in read_bgl(log_path, limit=limit, offset=offset):
        st["n_lines"] += 1
        text = raw.rstrip("\r\n")
        if "�" in text:
            st["replaced_char_lines"] += 1
        if not text.isascii():
            st["non_ascii_lines"] += 1
        h = hash(text)
        if h in seen:
            st["duplicate_lines"] += 1
        else:
            seen.add(h)
        rec = parse_line(text)
        if rec is None:
            st["malformed"] += 1
            if len(rejects) < 1000:
                rejects.append(f"{line_id}\t{text[:500]}")
            rows.append({"line_id": line_id, "label": None, "is_alert": False, "ts": None, "date": None,
                         "node": None, "time_full": None, "type": None, "component": None, "level": None,
                         "content": text, "parse_ok": False, "has_node_repeat": False})
        else:
            rec["line_id"] = line_id
            rows.append(rec)
            if rec["content"] == "":
                st["empty_content"] += 1
            if len(rec["content"]) > LONG_MSG:
                st["long_messages"] += 1
            if not rec["has_node_repeat"]:
                st["missing_node_repeat"] += 1
            ts = rec["ts"]
            if prev_ts is not None:
                if ts < prev_ts:
                    st["ts_out_of_order"] += 1
                elif ts - prev_ts > GAP_SECONDS:
                    gaps.append({"after_line_id": line_id - 1, "gap_seconds": ts - prev_ts, "ts_before": prev_ts, "ts_after": ts})
            prev_ts = max(ts, prev_ts) if prev_ts is not None else ts
            t = rec["time_full"]
            epoch = calendar.timegm((int(t[0:4]), int(t[5:7]), int(t[8:10]), int(t[11:13]), int(t[14:16]), int(t[17:19])))
            offsets[ts - epoch] += 1
        if len(rows) >= chunk_rows:
            flush()
            log.info("parsed %s lines", f"{st['n_lines']:,}")
    flush()
    writer.close()
    rejects_path.write_text("\n".join(rejects) + ("\n" if rejects else ""), encoding="utf-8")
    # ts is Unix time (UTC). time_full is local lab time (PDT = UTC-7h, PST = UTC-8h), so the expected
    # difference is 25200 s or 28800 s (+-1 s). Anything else counts as a disagreement.
    ok = sum(c for d, c in offsets.items() if abs(d - 25200) <= 1 or abs(d - 28800) <= 1)
    st["ts_vs_time_full_other_offset"] = sum(offsets.values()) - ok
    st["ts_time_full_offset_counts"] = {str(k): v for k, v in offsets.most_common(5)}
    st["large_gaps"] = gaps
    return st


# --------------------------------------------------------------------------------------
# 3. EDA
# --------------------------------------------------------------------------------------
def burst_stats(alert_ts: np.ndarray, gap: int, big: int = 10) -> dict:
    """Group alert lines into bursts: consecutive alert lines no more than ``gap`` seconds apart."""
    if alert_ts.size == 0:
        return dict(n_bursts=0, share_alerts_in_bursts_ge10=0.0, share_alerts_in_bursts_ge2=0.0, median_burst_size=0)
    breaks = np.where(np.diff(alert_ts) > gap)[0] + 1
    sizes = np.diff(np.concatenate([[0], breaks, [alert_ts.size]]))
    return dict(n_bursts=int(sizes.size), median_burst_size=int(np.median(sizes)), max_burst_size=int(sizes.max()),
                share_alerts_in_bursts_ge10=float(sizes[sizes >= big].sum() / alert_ts.size),
                share_alerts_in_bursts_ge2=float(sizes[sizes >= 2].sum() / alert_ts.size))


def savefig(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def run_eda(parquet: Path, st: dict, cfg: dict, fig_dir: Path, tab_dir: Path, log) -> dict:
    sns.set_theme(style="whitegrid", context="notebook")
    ok_cols = ["line_id", "label", "is_alert", "ts", "node", "type", "component", "level", "parse_ok"]
    df = pq.read_table(parquet, columns=ok_cols).to_pandas()
    lens = pc.utf8_length(pq.read_table(parquet, columns=["content"]).column("content")).to_numpy(zero_copy_only=False)
    good = df[df["parse_ok"]].copy()
    n, n_alert = len(df), int(df["is_alert"].sum())
    good["dt"] = pd.to_datetime(good["ts"], unit="s")

    # --- tables ---------------------------------------------------------------------
    tag_counts = good.loc[good["is_alert"], "label"].value_counts()
    tag_tbl = tag_counts.rename_axis("alert_tag").reset_index(name="n_lines")
    tag_tbl["fewer_than_100"] = tag_tbl["n_lines"] < MIN_TAG_LINES
    tag_tbl.to_csv(tab_dir / "alert_tags.csv", index=False)

    field_rows = []
    for col in ["type", "component", "level"]:
        for v, c in good[col].value_counts().items():
            field_rows.append({"field": col, "value": v, "n_lines": int(c), "alert_rate": float(good.loc[good[col] == v, "is_alert"].mean())})
    pd.DataFrame(field_rows).to_csv(tab_dir / "field_values.csv", index=False)
    pd.DataFrame(st["large_gaps"]).to_csv(tab_dir / "time_gaps.csv", index=False)

    level_fatal = int((good["level"] == "FATAL").sum())
    fatal_non_alert = int(((good["level"] == "FATAL") & ~good["is_alert"]).sum())
    bursts = burst_stats(good.loc[good["is_alert"], "ts"].to_numpy(), cfg["eda"]["burst_gap_seconds"])

    audit = [
        ("malformed_lines (regex failed)", st["malformed"], "kept in parquet with parse_ok=False; first 1000 in rejects.txt"),
        ("empty_content (nothing after level)", st["empty_content"], "line is valid but the message is empty"),
        ("lines_with_replacement_char (undecodable bytes)", st["replaced_char_lines"], "read with errors='replace'"),
        ("non_ascii_lines", st["non_ascii_lines"], ""),
        ("duplicate_lines (exact, after the first copy)", st["duplicate_lines"], "ratio of all lines"),
        ("timestamps_out_of_order", st["ts_out_of_order"], "ts smaller than the highest ts seen so far"),
        ("time_gaps_over_1h", len(st["large_gaps"]), "see time_gaps.csv"),
        ("ts_vs_time_full_disagreement", st["ts_vs_time_full_other_offset"], "difference not 7h/8h (PDT/PST); see ts_time_full_offset_counts in results.json"),
        ("missing_node_repeat_field", st["missing_node_repeat"], "6th field absent; handled by the parser"),
        ("node_is_dash_NULL_or_UNKNOWN", int(good["node"].isin(["-", "NULL", "UNKNOWN_LOCATION"]).sum()), "no usable node/location"),
        ("distinct_alert_tags", int(tag_counts.size), ""),
        ("alert_tags_with_fewer_than_100_lines", int((tag_counts < MIN_TAG_LINES).sum()), "see alert_tags.csv"),
        ("messages_longer_than_1000_chars", st["long_messages"], f"max length {int(lens.max())}"),
        ("FATAL_level_lines_that_are_not_alerts", fatal_non_alert, f"of {level_fatal:,} FATAL lines: level is NOT the alert label"),
    ]
    pd.DataFrame([{"check": a, "count": int(b), "percent_of_lines": round(100 * b / st["n_lines"], 4), "note": c} for a, b, c in audit]
                 ).to_csv(tab_dir / "dirty_data_audit.csv", index=False)

    summary = {
        "n_lines": n, "n_alert_lines": n_alert, "alert_line_ratio": n_alert / n,
        "first_timestamp_utc": str(good["dt"].min()), "last_timestamp_utc": str(good["dt"].max()),
        "n_distinct_nodes": int(good["node"].nunique()), "n_distinct_components": int(good["component"].nunique()),
        "n_distinct_levels": int(good["level"].nunique()), "n_distinct_alert_tags": int(tag_counts.size),
        "median_message_chars": float(np.median(lens)), "max_message_chars": int(lens.max()),
        "fatal_level_lines": level_fatal, "fatal_level_not_alert": fatal_non_alert,
    }

    # --- figures (Indonesian titles) -----------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.bar(["Non-alert", "Alert"], [n - n_alert, n_alert], color=["#4C78A8", "#E45756"])
    for i, v in enumerate([n - n_alert, n_alert]):
        ax.text(i, v, f"{v:,}\n({100 * v / n:.2f}%)", ha="center", va="bottom")
    ax.set_title("Proporsi baris alert vs non-alert"); ax.set_ylabel("Jumlah baris log"); ax.set_ylim(0, n * 1.15)
    savefig(fig, fig_dir / "eda_alert_ratio.png")

    top = tag_counts.head(20)[::-1]
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.barh(top.index, top.values, color="#E45756"); ax.set_xscale("log")
    ax.set_title("20 tag alert teratas"); ax.set_xlabel("Jumlah baris (skala log)"); ax.set_ylabel("Tag alert")
    savefig(fig, fig_dir / "eda_alert_tags.png")

    day = good["dt"].dt.floor("D")
    per_day = day.value_counts().sort_index(); per_day_alert = day[good["is_alert"]].value_counts().reindex(per_day.index, fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(per_day.index, per_day.values, width=0.9, color="#9ecae1", label="Semua baris")
    ax.bar(per_day_alert.index, per_day_alert.values, width=0.9, color="#E45756", label="Baris alert")
    ax.set_yscale("log"); ax.set_title("Jumlah baris log per hari (alert ditumpuk)"); ax.set_xlabel("Tanggal"); ax.set_ylabel("Baris per hari (skala log)"); ax.legend()
    savefig(fig, fig_dir / "eda_lines_per_day.png")

    hour = good.loc[good["is_alert"], "dt"].dt.floor("h").value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.vlines(hour.index, 0.5, hour.values, color="#E45756", linewidth=1.2)
    ax.set_yscale("log"); ax.set_ylim(0.5, hour.max() * 2)
    ax.set_title(f"Alert per jam: sangat bergerombol ({100 * bursts['share_alerts_in_bursts_ge10']:.1f}% alert ada di gelombang >=10 baris)")
    ax.set_xlabel("Waktu"); ax.set_ylabel("Baris alert per jam (skala log)")
    savefig(fig, fig_dir / "eda_alert_bursts.png")

    ct = good.groupby(["level", "is_alert"]).size().unstack(fill_value=0).rename(columns={False: "Non-alert", True: "Alert"})
    ct = ct.reindex(columns=["Non-alert", "Alert"], fill_value=0)
    ct = ct[ct.sum(axis=1) >= 100].sort_values("Non-alert", ascending=False)  # drop junk levels from corrupted lines
    ct.columns.name = None
    ax = ct.plot(kind="bar", figsize=(8, 4.5), color=["#4C78A8", "#E45756"], logy=True)
    ax.set_title("Level log menurut status alert (FATAL bukan sama dengan alert)"); ax.set_xlabel("Level"); ax.set_ylabel("Jumlah baris (skala log)")
    plt.xticks(rotation=0); savefig(ax.figure, fig_dir / "eda_level_by_alert.png")

    comp = good.groupby("component").agg(n=("is_alert", "size"), alert_rate=("is_alert", "mean")).sort_values("n", ascending=False).head(10)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].bar(comp.index, comp["n"], color="#4C78A8"); axes[0].set_yscale("log"); axes[0].set_title("Jumlah baris per komponen"); axes[0].set_ylabel("Baris (skala log)")
    axes[1].bar(comp.index, comp["alert_rate"] * 100, color="#E45756"); axes[1].set_title("Persentase alert per komponen"); axes[1].set_ylabel("% baris alert")
    for a in axes:
        a.set_xlabel("Komponen"); a.tick_params(axis="x", rotation=45)
    savefig(fig, fig_dir / "eda_component.png")

    nodes = good.groupby("node").agg(n=("is_alert", "size"), alert_rate=("is_alert", "mean"))
    by_vol = nodes.sort_values("n", ascending=False).head(20)[::-1]
    by_rate = nodes[nodes["n"] >= 1000].sort_values("alert_rate", ascending=False).head(20)[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5))
    axes[0].barh(by_vol.index, by_vol["n"], color="#4C78A8"); axes[0].set_title("20 node dengan baris terbanyak"); axes[0].set_xlabel("Jumlah baris")
    axes[1].barh(by_rate.index, by_rate["alert_rate"] * 100, color="#E45756"); axes[1].set_title("20 node dengan % alert tertinggi (min. 1.000 baris)"); axes[1].set_xlabel("% baris alert")
    axes[0].ticklabel_format(axis="x", style="plain"); axes[0].tick_params(axis="x", rotation=45)
    for a in axes:
        a.set_ylabel("Node"); a.tick_params(axis="y", labelsize=7)
    savefig(fig, fig_dir / "eda_top_nodes.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(lens, bins=60, color="#4C78A8"); ax.set_yscale("log")
    ax.set_title("Distribusi panjang pesan log"); ax.set_xlabel("Panjang pesan (karakter)"); ax.set_ylabel("Jumlah baris (skala log)")
    savefig(fig, fig_dir / "eda_msg_length.png")

    pd.DataFrame(list(summary.items()), columns=["metric", "value"]).to_csv(tab_dir / "dataset_summary.csv", index=False)
    log.info("EDA done: %d figures, tables in %s", len(list(fig_dir.glob('eda_*.png'))), tab_dir)
    return {"summary": summary, "bursts": bursts, "audit": {a.split(" ")[0]: int(b) for a, b, _ in audit}}


# --------------------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--sample", action="store_true", help="process only a contiguous slice (see config sample.*)")
    ap.add_argument("--force", action="store_true", help="recompute everything")
    args = ap.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg["seed"])
    ensure_dirs(cfg)
    log = get_logger("s01", cfg)
    zip_path, log_path = ensure_raw(cfg, log, False)  # --force recomputes parsing/EDA only, never re-downloads

    interim = get_path(cfg, "interim_dir")
    reports = get_path(cfg, "reports_dir")
    tag = "_sample" if args.sample else ""
    parquet, stats_path, rejects = interim / f"parsed{tag}.parquet", interim / f"s01_stats{tag}.json", interim / f"rejects{tag}.txt"
    fig_dir = reports / ("sample/figures" if args.sample else "figures")
    tab_dir = reports / ("sample/tables" if args.sample else "tables")
    fig_dir.mkdir(parents=True, exist_ok=True); tab_dir.mkdir(parents=True, exist_ok=True)
    limit, offset = (cfg["sample"]["lines"], cfg["sample"]["offset"]) if args.sample else (None, 0)

    if parquet.exists() and stats_path.exists() and not args.force:
        log.info("Using cached %s", parquet)
        st = json.loads(stats_path.read_text())
    else:
        st = parse_and_audit(log_path, parquet, rejects, cfg, log, limit, offset)
        stats_path.write_text(json.dumps(st))

    # sanity check against published figures (stop-and-ask if > tolerance); full run only
    n_parquet = pq.ParquetFile(parquet).metadata.num_rows
    assert n_parquet == st["n_lines"], "parquet rows must equal the line count"
    res = run_eda(parquet, st, cfg, fig_dir, tab_dir, log)
    summ = res["summary"]
    if not args.sample:
        tol = cfg["data"]["tolerance"]
        for key, exp in [("n_lines", cfg["data"]["expected_lines"]), ("n_alert_lines", cfg["data"]["expected_alert_lines"])]:
            if abs(summ[key] - exp) / exp > tol:
                log.error("%s=%s differs from expected %s by more than %.0f%%. STOP: write docs/BLOCKERS.md and ask Nafi.", key, summ[key], exp, tol * 100)
                raise SystemExit(3)
        results_path = reports / "results.json"
        results = json.loads(results_path.read_text()) if results_path.exists() else {}
        results["dataset"] = {
            **summ, "file_size_bytes": log_path.stat().st_size,
            "zip_size_bytes": zip_path.stat().st_size if zip_path.exists() else None,
            "sha256_log": sha256(log_path), "sha256_zip": sha256(zip_path) if zip_path.exists() else None,
            "source": cfg["data"]["zenodo_url"], "alert_bursts": res["bursts"],
        }
        results["dirty_data"] = {
            **res["audit"], "duplicate_line_ratio": st["duplicate_lines"] / st["n_lines"],
            "ts_time_full_offset_counts": st["ts_time_full_offset_counts"], "n_time_gaps_over_1h": len(st["large_gaps"]),
        }
        results_path.write_text(json.dumps(results, indent=2) + "\n")
        log.info("results.json updated (dataset, dirty_data)")
    log.info("S01 done. lines=%s alerts=%s (%.2f%%)", f"{summ['n_lines']:,}", f"{summ['n_alert_lines']:,}", 100 * summ["alert_line_ratio"])


if __name__ == "__main__":
    sys.exit(main())
