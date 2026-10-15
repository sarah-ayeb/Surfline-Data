"""Immutable raw layer. Path is keyed by the hour bucket, so re-running within the same
hour overwrites the same logical record (idempotent) instead of duplicating it."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def hour_bucket(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y-%m-%dT%H00Z")


def write_raw(root: Path, source: str, spot_id: int, payload: dict, meta: dict,
              now: datetime) -> Path:
    d = root / source / f"spot_id={spot_id}" / f"ingested_at={hour_bucket(now)}"
    d.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, sort_keys=True).encode()
    (d / "response.json").write_bytes(body)
    meta = {**meta, "fetched_at": now.astimezone(UTC).isoformat(),
            "sha256": hashlib.sha256(body).hexdigest(), "source": source, "spot_id": spot_id}
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    return d
