"""Canonical variables (SI units, UTC) and plausibility ranges."""
from datetime import datetime

from pydantic import BaseModel

# raw API field -> canonical name (unit is encoded in the name)
VARIABLES = {
    "marine": {
        "wave_height": "wave_height_m",
        "wave_period": "wave_period_s",
        "wave_direction": "wave_dir_deg",
        "swell_wave_height": "swell_height_m",
    },
    "weather": {
        "temperature_2m": "air_temp_c",
        "wind_speed_10m": "wind_speed_ms",
        "wind_direction_10m": "wind_dir_deg",
        "weather_code": "weather_code",
    },
}

RANGES = {
    "wave_height_m": (0, 30),
    "wave_period_s": (0, 30),
    "wave_dir_deg": (0, 360),
    "swell_height_m": (0, 30),
    "air_temp_c": (-50, 60),
    "wind_speed_ms": (0, 80),
    "wind_dir_deg": (0, 360),
    "weather_code": (0, 99),
}


class Condition(BaseModel):
    spot_id: int
    valid_time: datetime  # UTC
    variable: str
    value: float | None
    kind: str  # 'forecast' (valid_time after fetch) or 'analysis' (at or before fetch)
    source: str
    issued_at: datetime  # when we fetched it
    raw_id: str  # lineage: relative path of the raw payload
    quality_flag: str  # 'ok' | 'missing'
