import sys
from unittest.mock import MagicMock

# Mock mpv module to avoid OSError if libmpv is missing during tests
sys.modules["mpv"] = MagicMock()

from core.player import MpvPlayer  # noqa: E402
from core.types import Track  # noqa: E402


def test_mpv_player_init() -> None:
    player = MpvPlayer(wid=12345)

    # Verify MPV was initialized with correct wid and hardware decoding options
    import mpv
    mpv.MPV.assert_called_with(
        wid="12345",
        hwdec="auto-safe",
        vo="gpu",
        terminal="no",
        msg_level="all=no",
        input_default_bindings="no",
        input_vo_keyboard="no",
        cursor_autohide="no",
        volume_max="200",
    )

    assert player.mpv.keep_open is True
    assert player.mpv.lavfi_complex == ""


def test_mpv_player_open() -> None:
    player = MpvPlayer()
    player.mpv.track_list = [
        {"type": "audio", "id": 1, "lang": "eng", "codec": "aac"}
    ]
    player.open("test.mkv")

    player.mpv.play.assert_called_once_with("test.mkv")
    assert player.get_tracks() == [
        Track(index=1, language="eng", codec="aac")
    ]


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


def test_mpv_player_set_blanket_fill() -> None:
    player = MpvPlayer()
    player._video_w = 1920
    player._video_h = 1080

    # 1. Wider window -> generates blur filter
    player.set_blanket_fill(2560, 1080, True)
    assert "[vid1] split=3" in player.mpv.lavfi_complex
    assert "[vo]" in player.mpv.lavfi_complex

    # 2. Matching window (no black bars) -> passthrough null filter
    player.set_blanket_fill(1920, 1080, True)
    assert player.mpv.lavfi_complex == "[vid1] null [vo]"

    # 3. Disabled -> stays on null filter to prevent dropping video track
    player.set_blanket_fill(1920, 1080, False)
    assert player.mpv.lavfi_complex == "[vid1] null [vo]"

