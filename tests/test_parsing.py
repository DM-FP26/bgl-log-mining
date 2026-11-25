from bgllog.parsing import parse_line, read_bgl

ALERT = "KERNDTLB 1117955293 2005.06.05 R20-M0-N2-C:J10-U11 2005-06-05-00.08.13.410695 R20-M0-N2-C:J10-U11 RAS KERNEL FATAL data TLB error interrupt\n"
NORMAL = "- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.675872 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction cache parity error corrected\n"
NO_REPEAT = "- 1119415930 2005.06.21 - 2005-06-21-21.52.10.214285 RAS KERNEL FATAL Kill job 20251 timed out. Block freed.\n"
EMPTY = "- 1120866514 2005.07.08 R02-M1-N8-C:J13-U01 2005-07-08-16.48.34.004234 R02-M1-N8-C:J13-U01 RAS KERNEL FATAL\n"


def test_alert_line():
    r = parse_line(ALERT)
    assert r["is_alert"] and r["label"] == "KERNDTLB" and r["level"] == "FATAL"
    assert r["content"] == "data TLB error interrupt" and r["has_node_repeat"]


def test_normal_line():
    r = parse_line(NORMAL)
    assert not r["is_alert"] and r["component"] == "KERNEL" and r["type"] == "RAS"
    assert r["ts"] == 1117838570 and r["content"].startswith("instruction cache")


def test_missing_node_repeat():
    r = parse_line(NO_REPEAT)
    assert not r["has_node_repeat"] and r["node"] == "-"
    assert (r["type"], r["component"], r["level"]) == ("RAS", "KERNEL", "FATAL")
    assert r["content"] == "Kill job 20251 timed out. Block freed."


def test_empty_content_is_kept():
    r = parse_line(EMPTY)
    assert r is not None and r["content"] == "" and r["level"] == "FATAL"


def test_malformed_line():
    assert parse_line("garbage") is None
    assert parse_line("- notanumber 2005.06.03 N 2005-06-03-15.42.50.1 N RAS KERNEL INFO x") is None


def test_odd_bytes_read_with_replace(tmp_path):
    p = tmp_path / "x.log"
    p.write_bytes(NORMAL.encode().replace(b"cache", b"ca\xffche"))
    (_, line), = list(read_bgl(p))
    assert "�" in line and parse_line(line)["parse_ok"]


def test_read_offset_limit(tmp_path):
    p = tmp_path / "x.log"
    p.write_text(NORMAL * 5)
    assert [i for i, _ in read_bgl(p, limit=2, offset=1)] == [1, 2]
