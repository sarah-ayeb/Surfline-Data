import csv
from pathlib import Path

from pydantic import BaseModel, Field


class Spot(BaseModel):
    spot_id: int
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    timezone: str
    beach_facing_deg: int = Field(ge=0, le=360)


def load_spots(path: Path) -> list[Spot]:
    with open(path, newline="", encoding="utf-8") as f:
        return [Spot(**row) for row in csv.DictReader(f)]
