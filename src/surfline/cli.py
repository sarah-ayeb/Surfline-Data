import argparse
import logging
import sys
from datetime import UTC, datetime

import httpx

from surfline.config import settings
from surfline.ingestion.openmeteo import SOURCES, fetch
from surfline.ingestion.raw_store import write_raw
from surfline.models import load_spots
from surfline.transform.parse import build_silver

log = logging.getLogger("surfline")


def ingest(sources: list[str], now: datetime | None = None, client: httpx.Client | None = None):
    """Per-spot failure isolation: one bad spot never aborts the others."""
    now = now or datetime.now(UTC)
    spots = load_spots(settings.spots_file)
    client = client or httpx.Client()
    ok, failed = 0, []
    for source in sources:
        for spot in spots:
            try:
                payload, meta = fetch(source, spot, client)
                write_raw(settings.raw_dir, source, spot.spot_id, payload, meta, now)
                ok += 1
            except Exception as exc:  # noqa: BLE001 - logged and counted, not swallowed
                log.error("ingest_failed source=%s spot_id=%s error=%s", source, spot.spot_id, exc)
                failed.append((source, spot.spot_id))
    log.info("ingest_done ok=%d failed=%d", ok, len(failed))
    return ok, failed


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="surfline")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ingest")
    i.add_argument("--source", choices=[*SOURCES, "all"], default="all")
    sub.add_parser("transform")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.cmd == "transform":
        stats = build_silver(settings.raw_dir, settings.silver_dir)
        print(stats)
        return 0
    _, failed = ingest(list(SOURCES) if args.source == "all" else [args.source])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
