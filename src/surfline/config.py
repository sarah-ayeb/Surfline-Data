from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    raw_dir: Path = Path("raw")
    silver_dir: Path = Path("silver")
    spots_file: Path = Path("data/spots.csv")
    http_timeout_s: float = 20.0
    max_retries: int = 4


settings = Settings()
