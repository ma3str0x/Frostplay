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

        kwargs: dict[str, str] = {}
        if wid is not None:
            kwargs["wid"] = str(wid)

        kwargs["volume_max"] = "150"
        self.mpv = mpv.MPV(**kwargs)
        # Keep open after file ends so we can seek back
        self.mpv.keep_open = True
        self.mpv.lavfi_complex = ""

    def open(self, filepath: str) -> None:
        self._tracks = inspect_tracks(filepath, ffprobe_path=self.ffprobe_path)
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

    def set_mix(self, lavfi_str: str) -> None:
        self.mpv.lavfi_complex = lavfi_str

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
