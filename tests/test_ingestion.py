import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from surfline import cli
from surfline.config import settings
from surfline.ingestion import openmeteo

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "marine_sample.json").read_text())
NOW = datetime(2026, 10, 14, 10, 17, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "raw_dir", tmp_path / "raw")
    monkeypatch.setattr(settings, "spots_file", Path("data/spots.csv"))
    monkeypatch.setattr(openmeteo.fetch.retry, "wait", lambda *_: 0, raising=False)


@respx.mock
def test_ingest_writes_raw_and_is_idempotent():
    respx.get(openmeteo.SOURCES["marine"]["url"]).mock(return_value=httpx.Response(200, json=FIXTURE))
    ok, failed = cli.ingest(["marine"], now=NOW)
    assert (ok, failed) == (4, [])
    files = sorted(settings.raw_dir.rglob("response.json"))
    assert len(files) == 4
    cli.ingest(["marine"], now=NOW)  # same hour: no duplicates
    assert len(sorted(settings.raw_dir.rglob("response.json"))) == 4
    meta = json.loads(files[0].with_name("meta.json").read_text())
    assert meta["status"] == 200 and len(meta["sha256"]) == 64


@respx.mock
def test_one_failing_spot_does_not_abort_others():
    def side_effect(request):
        if "latitude=36.954" in str(request.url):
            return httpx.Response(400, json={"error": True})  # permanent, no retry
        return httpx.Response(200, json=FIXTURE)

    respx.get(openmeteo.SOURCES["marine"]["url"]).mock(side_effect=side_effect)
    ok, failed = cli.ingest(["marine"], now=NOW)
    assert ok == 3 and failed == [("marine", 1)]


@respx.mock
def test_transient_error_is_retried():
    route = respx.get(openmeteo.SOURCES["marine"]["url"]).mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json=FIXTURE)])
    spot = cli.load_spots(settings.spots_file)[0]
    payload, _meta = openmeteo.fetch("marine", spot, httpx.Client())
    assert route.call_count == 2 and payload["hourly"]["wave_height"][0] == 1.4
