"""Field-level parsing of raw BGL log lines (no cleaning, no templates; that is S02).

Raw layout (verified on the real file in S01)::

    <label> <unix_ts> <date> <node> <time_full> [<node_repeat>] <type> <component> <level> [<content>]

Real-data quirks handled here:
* ``node_repeat`` is sometimes missing (for example node is ``-``); we detect it by comparing
  with ``node``.
* ``content`` can be empty (line ends after the level).
* ``node`` can be ``NULL`` or ``-``; ``type`` can be ``NULL``. These are kept as-is.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

_TS_RE = re.compile(r"^\d{9,11}$")
_DATE_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}\.\d{2}\.\d{2}\.\d+$")

COLUMNS = ["line_id", "label", "is_alert", "ts", "date", "node", "time_full", "type",
           "component", "level", "content", "parse_ok", "has_node_repeat"]


def parse_line(raw: str) -> dict | None:
    """Split one raw line into fields. Returns ``None`` if the line does not match the layout."""
    raw = raw.rstrip("\r\n")
    head = raw.split(" ", 5)
    if len(head) < 6:
        return None
    label, ts, date, node, time_full, rest = head
    if not (_TS_RE.match(ts) and _DATE_RE.match(date) and _TIME_RE.match(time_full)):
        return None
    first = rest.split(" ", 1)[0]
    has_repeat = first == node
    parts = rest.split(" ", 4 if has_repeat else 3)
    if has_repeat:
        if len(parts) < 4:
            return None
        _, typ, comp, level, *tail = parts
    else:
        if len(parts) < 3:
            return None
        typ, comp, level, *tail = parts
    content = tail[0] if tail else ""
    return {
        "label": label, "is_alert": label != "-", "ts": int(ts), "date": date, "node": node,
        "time_full": time_full, "type": typ, "component": comp, "level": level,
        "content": content, "parse_ok": True, "has_node_repeat": has_repeat,
    }


def read_bgl(path: str | Path, limit: int | None = None, offset: int = 0) -> Iterator[tuple[int, str]]:
    """Yield ``(line_id, raw_line)`` from a BGL log, UTF-8 with ``errors='replace'``.

    ``offset`` skips lines; ``limit`` caps how many lines are yielded. Streams, never loads the file.
    """
    with open(path, "r", encoding="utf-8", errors="replace", newline="\n") as fh:
        for i, line in enumerate(fh):
            if i < offset:
                continue
            if limit is not None and i >= offset + limit:
                break
            yield i, line


# ----------------------------------------------------------------------------------------
# S02: minimal cleaning + Drain3 templates
# ----------------------------------------------------------------------------------------
import hashlib  # noqa: E402
import json  # noqa: E402

import numpy as np  # noqa: E402

_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f�]")
_WS_RE = re.compile(r"\s+")
EMPTY_TOKEN = "<EMPTY>"


def clean_content(text: str) -> str:
    """Minimal cleaning: drop control/replacement characters, collapse whitespace, strip.

    An empty result becomes ``<EMPTY>`` so empty messages get their own template instead of vanishing.
    """
    out = _WS_RE.sub(" ", _CTRL_RE.sub("", text)).strip()
    return out or EMPTY_TOKEN


def build_template_miner(cfg: dict, persist_path: str | Path | None = None):
    """Drain3 ``TemplateMiner`` built in code from ``cfg['parsing']`` (no ini file)."""
    from drain3 import TemplateMiner
    from drain3.file_persistence import FilePersistence
    from drain3.masking import MaskingInstruction
    from drain3.template_miner_config import TemplateMinerConfig

    d = cfg["parsing"]["drain"]
    tmc = TemplateMinerConfig()
    tmc.drain_depth = d["depth"]
    tmc.drain_sim_th = d["sim_th"]
    tmc.drain_max_children = d["max_children"]
    tmc.profiling_enabled = False
    tmc.masking_instructions = [MaskingInstruction(m["regex"], m["name"]) for m in cfg["parsing"]["masks"]]
    handler = FilePersistence(str(persist_path)) if persist_path else None
    return TemplateMiner(handler, tmc)


def assign_event_ids(contents, cfg: dict, persist_path: str | Path | None = None, progress=None):
    """Assign a Drain3 ``event_id`` (cluster id, starts at 1) to every message.

    Only the *unique* cleaned messages are fed to Drain3, in first-appearance order. Identical
    messages cannot create new templates, so this gives the same clusters as a full pass, much faster.
    Returns ``(event_ids: int32 array, templates: dict[event_id] -> template text, stats: dict)``.
    The Drain3 state is saved to ``persist_path`` once at the end (a per-change snapshot is very slow).
    """
    import pandas as pd

    cleaned = pd.Series(contents, copy=False).map(clean_content)
    changed = int((cleaned != pd.Series(contents, copy=False)).sum())
    uniq = pd.unique(cleaned)  # first-appearance order
    tm = build_template_miner(cfg)
    mapping: dict[str, int] = {}
    for i, msg in enumerate(uniq):
        mapping[msg] = tm.add_log_message(msg)["cluster_id"]
        if progress and (i + 1) % 50_000 == 0:
            progress(i + 1, len(uniq), len(tm.drain.clusters))
    ids = cleaned.map(mapping).to_numpy(dtype=np.int32)
    # final template text (templates can evolve while parsing, so read them at the end)
    templates = {c.cluster_id: c.get_template() for c in tm.drain.clusters}
    if persist_path:
        from drain3.file_persistence import FilePersistence

        tm.persistence_handler = FilePersistence(str(persist_path))
        tm.save_state("final")
    stats = {"n_unique_messages": int(len(uniq)), "n_templates": len(templates), "lines_changed_by_cleaning": changed}
    return ids, templates, stats


def config_hash(cfg: dict, keys=("parsing", "windows", "vocab", "seed")) -> str:
    """Short hash of the config sections that determine the preprocessing result."""
    blob = json.dumps({k: cfg[k] for k in keys}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]
