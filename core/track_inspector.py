import json
import subprocess
import sys
from pathlib import Path

from core.types import Track


class TrackInspectorError(Exception):
    """Exception raised for errors in the TrackInspector."""
    pass


def inspect_tracks(filepath: str | Path, ffprobe_path: str = "ffprobe") -> list[Track]:
    """
    Inspect a video file and extract its audio tracks using ffprobe.

    Args:
        filepath: The path to the video file to inspect.
        ffprobe_path: The executable name or path for ffprobe.

    Returns:
        A list of Track objects representing the audio tracks in the file.

    Raises:
        TrackInspectorError: If ffprobe is not found, the file is invalid,
            or output cannot be parsed.
    """
    filepath_str = str(filepath)
    cmd = [
        ffprobe_path,
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "a",
        filepath_str
    ]

    try:
        creationflags = (
            int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if sys.platform == "win32" else 0
        )
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            creationflags=creationflags,
        )
    except FileNotFoundError as e:
        raise TrackInspectorError(f"ffprobe executable not found: {ffprobe_path}") from e
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() if e.stderr else ""
        raise TrackInspectorError(f"ffprobe failed with exit code {e.returncode}: {err}") from e

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise TrackInspectorError("Failed to parse ffprobe JSON output") from e

    streams = data.get("streams", [])
    tracks = []

    # mpv assigns aid starting from 1 for the audio tracks
    for index, stream in enumerate(streams, start=1):
        tags = stream.get("tags", {})
        language = tags.get("language", "unknown")
        codec = stream.get("codec_name", "unknown")

        tracks.append(Track(index=index, language=language, codec=codec))

    return tracks
