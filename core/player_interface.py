from abc import ABC, abstractmethod

from core.types import Track


class PlayerInterface(ABC):
    @abstractmethod
    def open(self, filepath: str) -> None:
        pass

    @abstractmethod
    def play_pause(self) -> None:
        pass

    @abstractmethod
    def seek(self, seconds: float, absolute: bool = True) -> None:
        pass

    @abstractmethod
    def get_tracks(self) -> list[Track]:
        pass

    @abstractmethod
    def set_mix(self, lavfi_str: str) -> None:
        pass

    @abstractmethod
    def get_position(self) -> float:
        pass

    @abstractmethod
    def get_duration(self) -> float:
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        pass

    @abstractmethod
    def set_volume(self, volume: int) -> None:
        pass
