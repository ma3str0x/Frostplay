from dataclasses import dataclass


@dataclass
class Track:
    index: int
    language: str
    codec: str


@dataclass
class MixSelection:
    index: int
    volume: float
    enabled: bool = True


@dataclass
class MixPreset:
    id: int | None
    name: str
    selections: list[MixSelection]
    created_at: str
