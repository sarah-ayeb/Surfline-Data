# surfline-data
Data pipeline behind the Surfline dashboard. Current stage: Phase 2 (raw -> silver cleaning and validation).

## Quick start
```
python -m venv .venv && source .venv/bin/activate
make install
make test
cp .env.example .env
make ingest        # writes immutable raw payloads to ./raw
```
Raw layout: `raw/<source>/spot_id=<id>/ingested_at=<hour>/{response.json,meta.json}`

## Conventions
SI units + UTC internally; convert at presentation. Raw data is never modified.
Spot coordinates in `data/spots.csv` are placeholders: confirm with the product owner.
See `docs/` for ADRs and the source inventory.

## Phase 2: transform
```
python -m surfline.cli transform
```
Rebuilds `silver/conditions.jsonl` and `silver/rejected_records.jsonl` from the whole raw layer
(idempotent). Nulls are kept with `quality_flag=missing`; out-of-range or malformed values go to
`rejected_records` with a reason and the `raw_id` of the source payload (lineage).
