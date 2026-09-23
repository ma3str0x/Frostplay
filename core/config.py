import json
import os
from dataclasses import dataclass


@dataclass
class Config:
    mpv_path: str | None = None
    ffmpeg_path: str | None = None


def load_config(config_path: str = "config.json") -> Config:
    if not os.path.exists(config_path):
        return Config()

    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    return Config(
        mpv_path=data.get("mpv_path"),
        ffmpeg_path=data.get("ffmpeg_path")
    )
