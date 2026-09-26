import re

from core.blanket_fill import compute_blanket_fill_filter


def test_blanket_fill_zero_dimensions() -> None:
    assert compute_blanket_fill_filter(0, 0, 1920, 1080) is None
    assert compute_blanket_fill_filter(1920, 1080, 0, 0) is None
    assert compute_blanket_fill_filter(-100, 500, 1920, 1080) is None


def test_blanket_fill_matching_aspect_ratio() -> None:
    # 16:9 window with 16:9 video should not generate blanket fill bars
    assert compute_blanket_fill_filter(1920, 1080, 1920, 1080) is None
    assert compute_blanket_fill_filter(1280, 720, 1920, 1080) is None


def test_blanket_fill_horizontal_pillarbox() -> None:
    # Ultrawide window with 16:9 video -> side bars
    filt = compute_blanket_fill_filter(2560, 1080, 1920, 1080)
    assert filt is not None
    assert "hstack=3" in filt
    assert "[vid1] split=3" in filt
    assert "[vo]" in filt

    # Verify all crop and scale arguments have even numbers
    for m in re.finditer(r"crop=(\d+):(\d+):(\d+):(\d+)", filt):
        w, h, x, y = map(int, m.groups())
        assert w % 2 == 0
        assert h % 2 == 0
        assert x % 2 == 0
        assert y % 2 == 0

    for m in re.finditer(r"scale=(\d+):(\d+)", filt):
        w, h = map(int, m.groups())
        assert w % 2 == 0
        assert h % 2 == 0


def test_blanket_fill_vertical_letterbox() -> None:
    # Tall / square window with 16:9 video -> top/bottom bars
    filt = compute_blanket_fill_filter(800, 1000, 1920, 1080)
    assert filt is not None
    assert "vstack=3" in filt
    assert "[vid1] split=3" in filt
    assert "[vo]" in filt

    for m in re.finditer(r"crop=(\d+):(\d+):(\d+):(\d+)", filt):
        w, h, x, y = map(int, m.groups())
        assert w % 2 == 0
        assert h % 2 == 0
        assert x % 2 == 0
        assert y % 2 == 0

    for m in re.finditer(r"scale=(\d+):(\d+)", filt):
        w, h = map(int, m.groups())
        assert w % 2 == 0
        assert h % 2 == 0
