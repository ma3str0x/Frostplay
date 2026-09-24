import json
import os
from dataclasses import dataclass, asdict


def get_app_dir() -> str:
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    else:
        base = os.path.join(os.path.expanduser('~'), '.config')
    path = os.path.join(base, "Frostplay")
    os.makedirs(path, exist_ok=True)
    return path


CONFIG_PATH = os.path.join(get_app_dir(), "config.json")
DB_PATH = os.path.join(get_app_dir(), "mixer.db")


@dataclass
class Config:
    mpv_path: str | None = None
    ffmpeg_path: str | None = None
    default_folder: str | None = None


def load_config(config_path: str = CONFIG_PATH) -> Config:
    if not os.path.exists(config_path):
        return Config()

    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return Config()

    return Config(
        mpv_path=data.get("mpv_path"),
        ffmpeg_path=data.get("ffmpeg_path"),
        default_folder=data.get("default_folder")
    )


def save_config(config: Config, config_path: str = CONFIG_PATH) -> None:
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=4)
