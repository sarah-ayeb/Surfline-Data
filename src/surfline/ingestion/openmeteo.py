"""Open-Meteo client. Verify current terms of use (commercial use needs a paid plan)."""
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from surfline.config import settings
from surfline.models import Spot

SOURCES = {
    "marine": {
        "url": "https://marine-api.open-meteo.com/v1/marine",
        "hourly": "wave_height,wave_period,wave_direction,swell_wave_height",
        "extra": {},
    },
    "weather": {
        "url": "https://api.open-meteo.com/v1/forecast",
        "hourly": "temperature_2m,wind_speed_10m,wind_direction_10m,weather_code",
        "extra": {"wind_speed_unit": "ms"},  # keep SI
    },
}


class TransientError(Exception):
    """Retryable: timeouts, 429, 5xx."""


def _params(source: str, spot: Spot) -> dict:
    cfg = SOURCES[source]
    return {"latitude": spot.lat, "longitude": spot.lon, "hourly": cfg["hourly"],
            "timezone": "UTC", "forecast_days": 3, **cfg["extra"]}


@retry(
    retry=retry_if_exception_type(TransientError),
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_random_exponential(multiplier=1, max=30),
    reraise=True,
)
def fetch(source: str, spot: Spot, client: httpx.Client) -> tuple[dict, dict]:
    """Return (payload, request_metadata). Raises TransientError for retryable failures."""
    url, params = SOURCES[source]["url"], _params(source, spot)
    try:
        resp = client.get(url, params=params, timeout=settings.http_timeout_s)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise TransientError(str(exc)) from exc
    if resp.status_code == 429 or resp.status_code >= 500:
        raise TransientError(f"HTTP {resp.status_code}")
    resp.raise_for_status()  # other 4xx: permanent, do not retry
    return resp.json(), {"url": str(resp.request.url), "status": resp.status_code}
