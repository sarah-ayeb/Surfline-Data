"""Raw -> silver. Pure functions + a full-rebuild runner (idempotent: same raw => same output)."""
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from surfline.transform.schema import RANGES, VARIABLES, Condition

log = logging.getLogger("surfline")


def _reject(raw_id, source, spot_id, reason, detail=""):
    return {"raw_id": raw_id, "source": source, "spot_id": spot_id, "reason": reason,
            "detail": str(detail)}


def _utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts).replace(tzinfo=UTC)


def parse_payload(source: str, spot_id: int, payload: dict, issued_at: datetime,
                  raw_id: str) -> tuple[list[Condition], list[dict]]:
    conditions: list[Condition] = []
    rejected: list[dict] = []
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
        return [], [_reject(raw_id, source, spot_id, "missing_hourly_block")]
    try:
        times = [_utc(t) for t in hourly["time"]]
    except (ValueError, TypeError) as exc:
        return [], [_reject(raw_id, source, spot_id, "bad_timestamp", exc)]

    for raw_name, canon in VARIABLES[source].items():
        values = hourly.get(raw_name)
        if values is None:
            rejected.append(_reject(raw_id, source, spot_id, "missing_variable", raw_name))
            continue
        if len(values) != len(times):
            rejected.append(_reject(raw_id, source, spot_id, "length_mismatch", raw_name))
            continue
        lo, hi = RANGES[canon]
        for t, v in zip(times, values):
            if v is None:
                flag, val = "missing", None
            elif isinstance(v, bool) or not isinstance(v, (int, float)):
                rejected.append(_reject(raw_id, source, spot_id, "non_numeric",
                                        f"{canon}@{t.isoformat()}={v!r}"))
                continue
            elif not lo <= v <= hi:
                rejected.append(_reject(raw_id, source, spot_id, "out_of_range",
                                        f"{canon}@{t.isoformat()}={v}"))
                continue
            else:
                flag, val = "ok", float(v)
            conditions.append(Condition(
                spot_id=spot_id, valid_time=t, variable=canon, value=val,
                kind="forecast" if t > issued_at else "analysis", source=source,
                issued_at=issued_at, raw_id=raw_id, quality_flag=flag))
    return conditions, rejected


def build_silver(raw_dir: Path, out_dir: Path) -> dict:
    """Rebuild silver from the whole raw layer. Dedup: latest issued_at wins per natural key."""
    best: dict[tuple, Condition] = {}
    rejected: list[dict] = []
    n_payloads = 0
    for resp in sorted(raw_dir.glob("*/spot_id=*/ingested_at=*/response.json")):
        d = resp.parent
        source = d.parent.parent.name
        if source not in VARIABLES:
            continue
        spot_id = int(d.parent.name.split("=", 1)[1])
        raw_id = d.relative_to(raw_dir).as_posix()
        n_payloads += 1
        try:
            payload = json.loads(resp.read_text(encoding="utf-8"))
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            issued_at = datetime.fromisoformat(meta["fetched_at"])
        except (OSError, ValueError, KeyError) as exc:
            rejected.append(_reject(raw_id, source, spot_id, "unreadable_raw", exc))
            continue
        conds, rej = parse_payload(source, spot_id, payload, issued_at, raw_id)
        rejected.extend(rej)
        for c in conds:
            key = (c.spot_id, c.valid_time, c.variable, c.kind, c.source)
            if key not in best or c.issued_at > best[key].issued_at:
                best[key] = c

    rows = [best[k] for k in sorted(best, key=lambda k: (k[0], k[1], k[2], k[3], k[4]))]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "conditions.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in rows), encoding="utf-8")
    (out_dir / "rejected_records.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rejected), encoding="utf-8")

    missing = sum(1 for r in rows if r.quality_flag == "missing")
    total = len(rows) + len(rejected)
    stats = {"payloads": n_payloads, "rows_out": len(rows), "rows_missing": missing,
             "rows_rejected": len(rejected),
             "rejection_rate": round(len(rejected) / total, 4) if total else 0.0}
    if stats["rejection_rate"] > 0.05:
        log.warning("high_rejection_rate %s", stats)
    log.info("transform_done %s", stats)
    return stats
