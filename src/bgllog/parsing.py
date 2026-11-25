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
