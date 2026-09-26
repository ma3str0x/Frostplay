from typing import Any

import mpv

from core.player_interface import PlayerInterface
from core.track_inspector import inspect_tracks
from core.types import Track


class MpvPlayer(PlayerInterface):
    def __init__(
        self,
        wid: int | None = None,
        ffprobe_path: str = "ffprobe"
    ) -> None:
        self.ffprobe_path = ffprobe_path
        self._tracks: list[Track] = []
        self._audio_lavfi: str = ""
        self._video_lavfi: str = ""
        self._blanket_fill_enabled: bool = False
        self._window_w: int = 0
        self._window_h: int = 0
        self._video_w: int = 0
        self._video_h: int = 0
        self._video_par: float = 1.0
        self._aspect_callback: Any = None

        kwargs: dict[str, str] = {}
        if wid is not None:
            kwargs["wid"] = str(wid)

        kwargs["volume_max"] = "200"
        self.mpv = mpv.MPV(**kwargs)
        # Keep open after file ends so we can seek back
        self.mpv.keep_open = True
        self.mpv.lavfi_complex = ""

        @self.mpv.property_observer('video-params')  # type: ignore[untyped-decorator]
        def on_video_params(name: str, value: Any) -> None:
            if value and 'w' in value and 'h' in value:
                # Capture base video dimensions when blur filter is not expanding them
                if not self._video_lavfi:
                    self._video_w = value['w']
                    self._video_h = value['h']
                    self._video_par = float(value.get('par', 1.0))
                if self._video_h > 0 and self._aspect_callback:
                    self._aspect_callback((self._video_w * self._video_par) / self._video_h)
        self._video_params_observer = on_video_params

    def open(self, filepath: str) -> None:
        self._tracks = inspect_tracks(filepath, ffprobe_path=self.ffprobe_path)
        self._video_lavfi = ""
        self._audio_lavfi = ""
        self._video_w = 0
        self._video_h = 0
        self.mpv.lavfi_complex = ""
        try:
            self.mpv.vid = 1
        except Exception:
            pass
        self.mpv.play(filepath)

    def play_pause(self) -> None:
        self.mpv.pause = not self.mpv.pause

    def seek(self, seconds: float, absolute: bool = True) -> None:
        if absolute:
            self.mpv.time_pos = seconds
        else:
            self.mpv.seek(seconds)

    def get_tracks(self) -> list[Track]:
        return self._tracks

    def _apply_lavfi(self) -> None:
        parts = []
        if self._video_lavfi:
            parts.append(self._video_lavfi)
        if self._audio_lavfi:
            parts.append(self._audio_lavfi)
        combined = ";".join(parts)

        pos = self.get_position()
        was_playing = self.is_playing()

        try:
            self.mpv.lavfi_complex = combined
            if not self._video_lavfi:
                try:
                    self.mpv.command("set", "vid", "auto")
                except Exception:
                    pass
            if pos > 0 and self.mpv.time_pos is not None:
                if abs(self.get_position() - pos) > 1.5:
                    self.seek(pos, absolute=True)
            if was_playing and self.mpv.pause:
                self.mpv.pause = False
        except Exception:
            # Fall back safely to audio-only if video filter fails
            self._video_lavfi = ""
            try:
                self.mpv.lavfi_complex = self._audio_lavfi
                self.mpv.command("set", "vid", "auto")
                if was_playing and self.mpv.pause:
                    self.mpv.pause = False
            except Exception:
                pass


    def set_mix(self, lavfi_str: str) -> None:
        self._audio_lavfi = lavfi_str
        self._apply_lavfi()

    def set_blanket_fill(self, window_w: int, window_h: int, enabled: bool) -> None:
        self._window_w = window_w
        self._window_h = window_h
        self._blanket_fill_enabled = enabled

        new_video_lavfi = ""
        if enabled and self._video_w > 0 and self._video_h > 0 and window_w > 0 and window_h > 0:
            from core.blanket_fill import compute_blanket_fill_filter
            filter_str = compute_blanket_fill_filter(
                window_w, window_h, self._video_w, self._video_h, self._video_par
            )
            new_video_lavfi = filter_str if filter_str else "[vid1] null [vo]"
        elif self._video_h > 0 and self._video_lavfi:
            new_video_lavfi = "[vid1] null [vo]"

        if new_video_lavfi != self._video_lavfi:
            self._video_lavfi = new_video_lavfi
            self._apply_lavfi()

    def get_position(self) -> float:
        pos = self.mpv.time_pos
        return float(pos) if pos is not None else 0.0

    def get_duration(self) -> float:
        dur = self.mpv.duration
        return float(dur) if dur is not None else 0.0

    def is_playing(self) -> bool:
        return not self.mpv.pause

    def set_volume(self, volume: int) -> None:
        self.mpv.volume = volume

    def set_speed(self, speed: float) -> None:
        self.mpv.speed = speed

    def get_speed(self) -> float:
        val = getattr(self.mpv, 'speed', 1.0)
        return float(val) if val is not None else 1.0

    def close(self) -> None:
        self.mpv.command("stop")
        self._tracks = []
        self._audio_lavfi = ""
        self._video_lavfi = ""
        self.mpv.lavfi_complex = ""
        try:
            self.mpv.vid = 1
        except Exception:
            pass
        self.mpv.speed = 1.0
        self._video_w = 0
        self._video_h = 0
        self._video_par = 1.0

    def destroy(self) -> None:
        try:
            self.close()
            self.mpv.terminate()
        except Exception:
            pass

    def set_aspect_ratio_callback(self, callback: object) -> None:
        self._aspect_callback = callback

    def get_video_ratio(self) -> float:
        if self._video_w > 0 and self._video_h > 0:
            return float((self._video_w * self._video_par) / self._video_h)
        params = getattr(self.mpv, 'video_params', None)
        if params and 'w' in params and 'h' in params:
            h = params['h']
            if h > 0:
                return float(params['w'] / h)
        return 0.0
