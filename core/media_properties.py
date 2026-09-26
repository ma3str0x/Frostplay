import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MediaProperties:
    title: str = "-"
    subtitle: str = "-"
    artists: str = "-"
    length: str = "-"
    genre: str = "-"
    year: str = "-"
    resolution: str = "-"
    frame_rate: str = "-"
    audio_channels: str = "-"
    item_type: str = "-"
    file_location: str = "-"


def format_duration(seconds: float | None) -> str:
    if not seconds or seconds <= 0:
        return "00:00"
    total = int(round(seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def get_media_properties(filepath: str, player: Any = None) -> MediaProperties:
    props = MediaProperties()
    if not filepath or not os.path.exists(filepath):
        return props

    norm_path = os.path.abspath(filepath)
    props.file_location = norm_path
    _, ext = os.path.splitext(norm_path)
    props.item_type = ext.lower() if ext else "-"
    props.title = os.path.splitext(os.path.basename(norm_path))[0]

    # Year from file modification time
    try:
        mtime = os.path.getmtime(norm_path)
        props.year = datetime.fromtimestamp(mtime).strftime("%Y")
    except Exception:
        pass

    # 1. Fast, non-blocking extraction directly from active mpv instance
    if player is not None and hasattr(player, "mpv"):
        try:
            mpv = player.mpv

            dur = player.get_duration()
            if dur > 0:
                props.length = format_duration(dur)

            v_params = getattr(mpv, "video_params", None)
            if v_params and isinstance(v_params, dict):
                w = v_params.get("w")
                h = v_params.get("h")
                if w and h:
                    props.resolution = f"{w} × {h}"

            fps = getattr(mpv, "container_fps", None) or getattr(mpv, "estimated_vf_fps", None)
            if fps and fps > 0:
                props.frame_rate = f"{float(fps):.3f}".rstrip("0").rstrip(".")

            a_params = getattr(mpv, "audio_params", None)
            if a_params and isinstance(a_params, dict):
                channels = a_params.get("channel-count") or a_params.get("channels")
                if channels == 1:
                    props.audio_channels = "1 (mono)"
                elif channels == 2:
                    props.audio_channels = "2 (stereo)"
                elif channels == 6:
                    props.audio_channels = "6 (5.1 surround)"
                elif channels:
                    props.audio_channels = f"{channels} channels"

            meta = getattr(mpv, "metadata", None)
            if meta and isinstance(meta, dict):
                if meta.get("title"):
                    props.title = str(meta["title"])
                if meta.get("artist") or meta.get("album_artist"):
                    props.artists = str(meta.get("artist") or meta.get("album_artist"))
                if meta.get("genre"):
                    props.genre = str(meta["genre"])
                if meta.get("date") or meta.get("year"):
                    props.year = str(meta.get("date") or meta.get("year"))[:4]
                if meta.get("sub_title") or meta.get("comment"):
                    props.subtitle = str(meta.get("sub_title") or meta.get("comment"))
        except Exception:
            pass

    # 2. Only use ffprobe if essential video properties are still unknown
    if props.resolution == "-" or props.frame_rate == "-" or props.audio_channels == "-":
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bundled_ffprobe = os.path.join(project_dir, "ffprobe.exe")
        ffprobe_exe = bundled_ffprobe if os.path.exists(bundled_ffprobe) else "ffprobe"

        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        try:
            cmd = [
                ffprobe_exe,
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                norm_path
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1.5,
                creationflags=creationflags
            )
            if res.returncode == 0:
                data = json.loads(res.stdout)
                format_info = data.get("format", {})
                streams = data.get("streams", [])

                if props.length == "-":
                    dur_str = format_info.get("duration")
                    if dur_str:
                        props.length = format_duration(float(dur_str))

                tags = format_info.get("tags", {})
                base_title = os.path.splitext(os.path.basename(norm_path))[0]
                if tags.get("title") and props.title == base_title:
                    props.title = tags["title"]
                if tags.get("artist") and props.artists == "-":
                    props.artists = tags["artist"]
                if tags.get("genre") and props.genre == "-":
                    props.genre = tags["genre"]
                if (tags.get("date") or tags.get("year")) and props.year == "-":
                    props.year = str(tags.get("date") or tags.get("year"))[:4]

                for s in streams:
                    codec_type = s.get("codec_type")
                    if codec_type == "video" and props.resolution == "-":
                        w = s.get("width")
                        h = s.get("height")
                        if w and h:
                            props.resolution = f"{w} × {h}"
                        r_fps = s.get("avg_frame_rate") or s.get("r_frame_rate")
                        if r_fps and "/" in r_fps:
                            num, den = r_fps.split("/")
                            if float(den) > 0:
                                calc_fps = float(num) / float(den)
                                if calc_fps > 0:
                                    props.frame_rate = f"{calc_fps:.3f}".rstrip("0").rstrip(".")
                    elif codec_type == "audio" and props.audio_channels == "-":
                        ch = s.get("channels")
                        layout = s.get("channel_layout", "")
                        if ch == 1:
                            props.audio_channels = "1 (mono)"
                        elif ch == 2:
                            props.audio_channels = "2 (stereo)"
                        elif ch:
                            desc = f"{ch} ({layout})" if layout else f"{ch} channels"
                            props.audio_channels = desc
        except Exception:
            pass

    return props
