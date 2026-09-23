
from core.player_interface import PlayerInterface
from core.types import Track


class FakePlayer(PlayerInterface):
    def __init__(self, tracks: list[Track]) -> None:
        self._tracks = tracks
        self.last_mix: str = ""
        self._is_playing: bool = False
        self.current_position: float = 0.0

    def is_playing(self) -> bool:
        return self._is_playing

    def open(self, filepath: str) -> None:
        self._is_playing = False
        self.current_position = 0.0

    def play_pause(self) -> None:
        self._is_playing = not self._is_playing

    def seek(self, seconds: float, absolute: bool = True) -> None:
        if absolute:
            self.current_position = seconds
        else:
            self.current_position += seconds

    def get_tracks(self) -> list[Track]:
        return self._tracks

    def set_mix(self, lavfi_str: str) -> None:
        self.last_mix = lavfi_str

    def get_position(self) -> float:
        return self.current_position

    def get_duration(self) -> float:
        return 100.0  # Fake duration
