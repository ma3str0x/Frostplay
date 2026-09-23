import sys
from unittest.mock import MagicMock, patch

# Mock mpv module to avoid OSError if libmpv is missing during tests
sys.modules["mpv"] = MagicMock()

from core.player import MpvPlayer  # noqa: E402
from core.types import Track  # noqa: E402


def test_mpv_player_init() -> None:
    player = MpvPlayer(wid=12345)

    # Verify MPV was initialized with correct wid
    import mpv
    mpv.MPV.assert_called_with(wid="12345", volume_max="150")

    assert player.mpv.keep_open is True
    assert player.mpv.lavfi_complex == ""


@patch("core.player.inspect_tracks")
def test_mpv_player_open(mock_inspect_tracks: MagicMock) -> None:
    mock_inspect_tracks.return_value = [
        Track(index=1, language="eng", codec="aac")
    ]

    player = MpvPlayer()
    player.open("test.mkv")

    mock_inspect_tracks.assert_called_once_with("test.mkv", ffprobe_path="ffprobe")
    player.mpv.play.assert_called_once_with("test.mkv")
    assert player.get_tracks() == mock_inspect_tracks.return_value


def test_mpv_player_play_pause() -> None:
    player = MpvPlayer()
    player.mpv.pause = False

    player.play_pause()
    assert player.mpv.pause is True

    player.play_pause()
    assert player.mpv.pause is False


def test_mpv_player_seek() -> None:
    player = MpvPlayer()

    # Absolute seek
    player.seek(15.5, absolute=True)
    assert player.mpv.time_pos == 15.5

    # Relative seek
    player.seek(5.0, absolute=False)
    player.mpv.seek.assert_called_with(5.0)


def test_mpv_player_set_mix() -> None:
    player = MpvPlayer()
    player.set_mix("[aid1]volume=1.0[a1]")
    assert player.mpv.lavfi_complex == "[aid1]volume=1.0[a1]"


def test_mpv_player_get_position_and_duration() -> None:
    player = MpvPlayer()

    player.mpv.time_pos = 12.3
    assert player.get_position() == 12.3

    player.mpv.duration = 100.5
    assert player.get_duration() == 100.5

    # Test None handling
    player.mpv.time_pos = None
    assert player.get_position() == 0.0

    player.mpv.duration = None
    assert player.get_duration() == 0.0
