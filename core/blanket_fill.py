"""Module for computing blanket fill (blurred background) filter graph for mpv/ffmpeg.

Fills black bars (pillarbox/letterbox) with a high-contrast, blurred version of video edges
to provide a seamless modern background when window aspect ratio does not match video.
All crop and scale dimensions are strictly even (multiples of 2) for yuv420p compatibility.
Uses highly-optimized avgblur on compact buffer for zero playback lag and cinematic contrast.
"""


def _make_even(val: float | int) -> int:
    return max(2, (int(val) // 2) * 2)


def _make_even_offset(val: float | int) -> int:
    return max(0, (int(val) // 2) * 2)


def compute_blanket_fill_filter(
    window_w: int,
    window_h: int,
    video_w: int,
    video_h: int,
    par: float = 1.0,
    contrast: float = 1.50,
    brightness: float = -0.16,
    saturation: float = 1.35,
) -> str | None:
    """Compute ffmpeg lavfi complex filter string for blurred black bars fill.

    Args:
        window_w: Current display window width.
        window_h: Current display window height.
        video_w: Original video width.
        video_h: Original video height.
        par: Pixel aspect ratio (default 1.0).
        contrast: Contrast boost (default 1.50 for rich visual separation).
        brightness: Brightness adjustment (default -0.16 for deep, dark backdrop).
        saturation: Color saturation boost (default 1.35 for vibrant ambient glow).

    Returns:
        ffmpeg lavfi string routing [vid1] -> [vo], or None if no bars exist.
    """
    if window_w <= 0 or window_h <= 0 or video_w <= 0 or video_h <= 0:
        return None
    if par <= 0:
        par = 1.0

    video_w = _make_even(video_w)
    video_h = _make_even(video_h)

    video_aspect = (video_w * par) / video_h
    window_aspect = window_w / window_h

    # If aspect ratios match closely, black bars are negligible (< 3% difference)
    if abs(window_aspect - video_aspect) < 0.03:
        return None

    split = "[vid1] split=3 [a] [v] [b]"
    eq_filter = f"eq=contrast={contrast:.2f}:brightness={brightness:.2f}:saturation={saturation:.2f}"
    blur_filter = "avgblur=sizeX=15:sizeY=15"

    if window_aspect > video_aspect:
        # Window is wider than video -> horizontal black bars (left & right pillarbox)
        total_blur = int((window_w / window_h) * video_h / par - video_w)
        blur_size = _make_even(total_blur // 2)

        height_with_max_w = (video_h / video_w) * window_w
        if height_with_max_w <= 0:
            return None
        visible_height = _make_even(video_h * par * window_h / height_with_max_w)
        visible_width = _make_even(blur_size * window_h / height_with_max_w)

        if visible_width <= 0 or visible_height <= 0 or blur_size < 4:
            return None
        if visible_height > video_h:
            visible_height = video_h
        if visible_width > video_w:
            visible_width = video_w

        offset_y = _make_even_offset((video_h - visible_height) // 2)
        offset_x2 = _make_even_offset(video_w - visible_width)

        down_w, down_h = 32, 48

        crop_1 = f"crop={visible_width}:{visible_height}:0:{offset_y}"
        proc_1 = (
            f"{crop_1},"
            f"scale={down_w}:{down_h}:flags=fast_bilinear,"
            f"{blur_filter},{eq_filter},"
            f"scale={blur_size}:{video_h}:flags=bilinear"
        )

        crop_2 = f"crop={visible_width}:{visible_height}:{offset_x2}:{offset_y}"
        proc_2 = (
            f"{crop_2},"
            f"scale={down_w}:{down_h}:flags=fast_bilinear,"
            f"{blur_filter},{eq_filter},"
            f"scale={blur_size}:{video_h}:flags=bilinear"
        )

        stack_direction = "h"
    else:
        # Window is taller than video -> vertical black bars (top & bottom letterbox)
        total_blur = int((window_h / window_w) * video_w * par - video_h)
        blur_size = _make_even(total_blur // 2)

        width_with_max_h = (video_w / video_h) * window_h
        if width_with_max_h <= 0:
            return None
        visible_width = _make_even(video_w * window_w / width_with_max_h)
        visible_height = _make_even(blur_size * window_w / width_with_max_h)

        if visible_width <= 0 or visible_height <= 0 or blur_size < 4:
            return None
        if visible_width > video_w:
            visible_width = video_w
        if visible_height > video_h:
            visible_height = video_h

        offset_x = _make_even_offset((video_w - visible_width) // 2)
        offset_y2 = _make_even_offset(video_h - visible_height)

        down_w, down_h = 48, 32

        crop_1 = f"crop={visible_width}:{visible_height}:{offset_x}:0"
        proc_1 = (
            f"{crop_1},"
            f"scale={down_w}:{down_h}:flags=fast_bilinear,"
            f"{blur_filter},{eq_filter},"
            f"scale={video_w}:{blur_size}:flags=bilinear"
        )

        crop_2 = f"crop={visible_width}:{visible_height}:{offset_x}:{offset_y2}"
        proc_2 = (
            f"{crop_2},"
            f"scale={down_w}:{down_h}:flags=fast_bilinear,"
            f"{blur_filter},{eq_filter},"
            f"scale={video_w}:{blur_size}:flags=bilinear"
        )

        stack_direction = "v"

    zone_1 = f"[a] {proc_1} [a_fin]"
    zone_2 = f"[b] {proc_2} [b_fin]"
    par_fix = f"setsar=ratio={par}:max=10000"
    stack = f"[a_fin] [v] [b_fin] {stack_direction}stack=3,{par_fix} [vo]"

    return f"{split};{zone_1};{zone_2};{stack}"
