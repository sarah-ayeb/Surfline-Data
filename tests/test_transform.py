import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from surfline.ingestion.raw_store import write_raw
from surfline.transform.parse import build_silver, parse_payload

FIX = Path(__file__).parent / "fixtures"
MARINE = json.loads((FIX / "marine_sample.json").read_text())
WEATHER = json.loads((FIX / "weather_sample.json").read_text())
T0 = datetime(2026, 10, 13, 0, 30, tzinfo=UTC)


def test_parse_marine_ok():
    conds, rej = parse_payload("marine", 1, MARINE, T0, "r")
    assert rej == [] and len(conds) == 8
    first = next(c for c in conds if c.variable == "wave_height_m")
    assert first.value == 1.4 and first.kind == "analysis"  # 00:00 <= fetch 00:30
    later = [c for c in conds if c.variable == "wave_height_m"][1]
    assert later.kind == "forecast"


def test_null_is_kept_as_missing_not_zero():
    p = deepcopy(MARINE)
    p["hourly"]["wave_height"][0] = None
    conds, rej = parse_payload("marine", 1, p, T0, "r")
    c = next(c for c in conds if c.variable == "wave_height_m")
    assert c.value is None and c.quality_flag == "missing" and rej == []


def test_out_of_range_is_rejected_with_reason():
    p = deepcopy(WEATHER)
    p["hourly"]["wind_speed_10m"][0] = 500
    conds, rej = parse_payload("weather", 1, p, T0, "r")
    assert [r["reason"] for r in rej] == ["out_of_range"]
    assert len(conds) == 7


def test_structural_problems_are_rejected():
    assert parse_payload("marine", 1, {}, T0, "r")[1][0]["reason"] == "missing_hourly_block"
    p = deepcopy(MARINE)
    p["hourly"]["wave_period"].pop()
    _, rej = parse_payload("marine", 1, p, T0, "r")
    assert rej[0]["reason"] == "length_mismatch"
    p = deepcopy(MARINE)
    del p["hourly"]["wave_direction"]
    _, rej = parse_payload("marine", 1, p, T0, "r")
    assert rej[0]["reason"] == "missing_variable"


def test_build_silver_dedup_and_idempotent(tmp_path):
    raw, out = tmp_path / "raw", tmp_path / "silver"
    meta = {"url": "u", "status": 200}
    write_raw(raw, "marine", 1, MARINE, meta, datetime(2026, 10, 13, 0, 30, tzinfo=UTC))
    newer = deepcopy(MARINE)
    newer["hourly"]["wave_height"][1] = 1.9  # revised forecast
    write_raw(raw, "marine", 1, newer, meta, datetime(2026, 10, 13, 1, 30, tzinfo=UTC))
    write_raw(raw, "weather", 1, WEATHER, meta, T0)
    stats = build_silver(raw, out)
    assert stats["payloads"] == 3 and stats["rows_rejected"] == 0
    rows = [json.loads(line) for line in (out / "conditions.jsonl").read_text().splitlines()]
    h1 = [r for r in rows if r["variable"] == "wave_height_m"
          and r["valid_time"].startswith("2026-10-13T01:00") and r["source"] == "marine"]
    # 01:00 was 'forecast' in run 1 (fetched 00:30) and 'analysis' in run 2 (fetched 01:30)
    assert {(r["kind"], r["value"]) for r in h1} == {("forecast", 1.5), ("analysis", 1.9)}
    first = (out / "conditions.jsonl").read_text()
    build_silver(raw, out)  # run twice => identical output
    assert (out / "conditions.jsonl").read_text() == first
