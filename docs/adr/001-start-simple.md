# ADR-001: Start with Python + files + Postgres; no orchestrator yet
Status: accepted. Data volume is small (hundreds of spots x hourly). Cron/GitHub Actions
schedule is enough for Phase 1-3. Revisit Dagster/Airflow at Phase 4 when backfills and
dependent steps appear. Raw payloads are stored immutably so everything is reprocessable.
