import json
import subprocess
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core.track_inspector import TrackInspectorError, inspect_tracks
from core.types import Track


def test_inspect_tracks_success() -> None:
    """Test successful extraction of audio tracks."""
    mock_json = {
        "streams": [
            {
                "codec_name": "aac",
                "tags": {"language": "eng"}
            },
            {
                "codec_name": "ac3",
                "tags": {"language": "ukr"}
            },
            {
                "codec_name": "mp3"
                # missing language tag
            }
        ]
    }

    mock_result = MagicMock()
    mock_result.stdout = json.dumps(mock_json)

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        tracks = inspect_tracks("dummy.mkv")

        mock_run.assert_called_once()
        assert len(tracks) == 3

        assert tracks[0] == Track(index=1, language="eng", codec="aac")
        assert tracks[1] == Track(index=2, language="ukr", codec="ac3")
        assert tracks[2] == Track(index=3, language="unknown", codec="mp3")


def test_inspect_tracks_ffprobe_missing() -> None:
    """Test behavior when ffprobe is not found."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(TrackInspectorError, match="ffprobe executable not found"):
            inspect_tracks("dummy.mkv")


def test_inspect_tracks_invalid_file() -> None:
    """Test behavior when ffprobe fails (e.g., file not found or invalid)."""
    mock_error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["ffprobe", "..."],
        stderr="No such file or directory"
    )
    with patch("subprocess.run", side_effect=mock_error):
        with pytest.raises(TrackInspectorError, match="ffprobe failed with exit code 1"):
            inspect_tracks("missing.mkv")


def test_inspect_tracks_invalid_json() -> None:
    """Test behavior when ffprobe returns invalid JSON."""
    mock_result = MagicMock()
    mock_result.stdout = "This is not JSON"

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(TrackInspectorError, match="Failed to parse ffprobe JSON output"):
            inspect_tracks("dummy.mkv")


def test_inspect_tracks_empty_streams() -> None:
    """Test behavior when a file has no audio streams."""
    mock_json: dict[str, list[Any]] = {"streams": []}
    mock_result = MagicMock()
    mock_result.stdout = json.dumps(mock_json)

    with patch("subprocess.run", return_value=mock_result):
        tracks = inspect_tracks("dummy.mkv")
        assert len(tracks) == 0
