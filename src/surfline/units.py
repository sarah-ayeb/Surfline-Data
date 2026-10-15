"""Canonical storage is SI (m, m/s, degC, degrees). Convert only at presentation."""
import math

COMPASS_16 = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def m_to_ft(m: float) -> float:
    return m * 3.28084


def ms_to_mph(ms: float) -> float:
    return ms * 2.236936


def deg_to_compass(deg: float) -> str:
    return COMPASS_16[int(((deg % 360) + 11.25) // 22.5) % 16]


def circular_mean_deg(degs: list[float]) -> float:
    """Never average angles arithmetically: 359 and 1 must give 0, not 180."""
    s = sum(math.sin(math.radians(d)) for d in degs)
    c = sum(math.cos(math.radians(d)) for d in degs)
    return math.degrees(math.atan2(s, c)) % 360
