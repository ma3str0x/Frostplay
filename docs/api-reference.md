# API Reference — Frostplay

Complete reference for all public modules, classes, and functions.

---

## `core/types.py` — Shared Data Types

### `Track`

```python
@dataclass
class Track:
    index: int       # Audio track index (mpv numbering: starts at 1)
    language: str    # Track language (ISO 639, e.g. "eng", "ukr")
    codec: str       # Codec (e.g. "aac", "ac3", "opus")
```

### `MixSelection`

```python
@dataclass
class MixSelection:
    index: int           # Track index
    volume: float        # Volume (0.0 – 1.0, where 1.0 = 100%)
    enabled: bool = True # Whether the track is enabled
```

### `MixPreset`

```python
@dataclass
class MixPreset:
    id: int | None                   # DB ID (None for new presets)
    name: str                        # Preset name
    selections: list[MixSelection]   # Track settings list
    created_at: str                  # ISO creation date
```

> **Note:** `MixPreset` is kept for backwards type compatibility, but the preset feature is currently deactivated.

---

## `core/player_interface.py` — Player Interface

### `PlayerInterface` (ABC)

Abstract base class for all player implementations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `open` | `(filepath: str) -> None` | Open a media file |
| `play_pause` | `() -> None` | Toggle playback/pause |
| `seek` | `(seconds: float, absolute: bool = True) -> None` | Seek. `absolute=True` — absolute position, `False` — relative |
| `get_tracks` | `() -> list[Track]` | Get list of audio tracks |
| `set_mix` | `(lavfi_str: str) -> None` | Set lavfi-complex filter |
| `get_position` | `() -> float` | Current playback position (seconds) |
| `get_duration` | `() -> float` | Total duration (seconds) |
| `is_playing` | `() -> bool` | Whether currently playing |
| `set_volume` | `(volume: int) -> None` | Set master volume (0–100) |

---

## `core/player.py` — MpvPlayer Implementation

### `MpvPlayer(PlayerInterface)`

Player implementation via `python-mpv` (libmpv).

**Constructor:**
```python
MpvPlayer(wid: int | None = None, ffprobe_path: str = "ffprobe")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `wid` | `int \| None` | Window ID for embedding video in a Qt widget |
| `ffprobe_path` | `str` | Path to ffprobe |

**Important details:**
- `volume_max` is set to `150` so mpv doesn't reject values >100
- `keep_open = True` — the window doesn't close after the file ends
- `inspect_tracks()` is automatically called on `open()`

---

## `core/fake_player.py` — Test Player

### `FakePlayer(PlayerInterface)`

Stub implementation for unit tests and CI (where libmpv and display are unavailable).

```python
FakePlayer(tracks: list[Track])
```

Stores the last lavfi string in `self.last_mix`, supports `play_pause()`, `seek()`.

---

## `core/mixer.py` — Filter Graph Builder

### `build_lavfi_complex(selections: list[MixSelection]) -> str`

Builds a `lavfi-complex` string for mpv from the array of selected tracks.

**Logic:**
- 0 enabled → `"anullsrc[ao]"` (silence)
- 1 enabled → `"[aid{i}]volume={v}[ao]"` (simple volume adjustment)
- N enabled → volume per track + `amix=inputs=N:duration=longest[ao]`

**Example:**
```python
selections = [
    MixSelection(index=1, volume=0.8, enabled=True),
    MixSelection(index=2, volume=0.5, enabled=True),
]
result = build_lavfi_complex(selections)
# "[aid1]volume=0.80[a0];[aid2]volume=0.50[a1];[a0][a1]amix=inputs=2:duration=longest[ao]"
```

---

## `core/track_inspector.py` — Track Inspection

### `inspect_tracks(filepath: str | Path, ffprobe_path: str = "ffprobe") -> list[Track]`

Runs `ffprobe` to get the list of audio tracks from a media file.

**Exceptions:** `TrackInspectorError`
- ffprobe not found
- Invalid file
- JSON parsing failure

---

## `core/config.py` — Configuration

### `Config`

```python
@dataclass
class Config:
    mpv_path: str | None = None
    ffmpeg_path: str | None = None
```

### `load_config(config_path: str = "config.json") -> Config`

Loads configuration from a JSON file. Returns a default `Config()` if the file doesn't exist.

---

## `db/schema.py` — Database Schema

### `init_db(db_path: str = "mixer.db") -> None`

Initializes the SQLite database. Creates tables if they don't exist:

| Table | Columns | Description |
|-------|---------|-------------|
| `schema_version` | `version INTEGER` | Schema version |
| `history` | `id, file_path TEXT, opened_at TEXT` | Opened files history |

---

## `db/history.py` — History Operations

### `add_to_history(file_path: str, db_path: str = "mixer.db") -> None`

Adds a record to the `history` table with the current date/time (ISO format).

### `get_history(limit: int = 50, db_path: str = "mixer.db") -> list[str]`

Returns unique file paths sorted by last opened date (newest first). Maximum `limit` records.

---

## `ui/main_window.py` — Main Window

### `MainWindow(FluentWindow)`

Main application window. Orchestrates all components and connects them via signals.

**Navigation pages:**

| Page | Icon | Position |
|------|------|----------|
| Player | `FIF.PLAY` | TOP |
| History | `FIF.HISTORY` | TOP |
| Settings | `FIF.SETTING` | BOTTOM |

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `←` | Seek −10s |
| `→` | Seek +10s |

**Internal slots:**

| Slot | Description |
|------|-------------|
| `_open_file(filepath)` | Open file, update tracks, save to history |
| `_on_mix_changed(selections)` | Build lavfi-complex and pass to player |
| `_on_master_volume_changed(volume)` | Change master volume |
| `_update_player_state()` | 500ms timer — update position/duration |
| `_show_tracks_menu()` | Show/hide TracksPanel |

---

## `ui/player_widget.py` — Video Widget

### `PlayerWidget(QWidget)`

Black widget into which mpv is embedded via `winId()`.

**Signals:**
- `clicked()` — left mouse button click (toggles play/pause)

---

## `ui/components/player_controls.py` — Control Bar

### `ClickableSlider(Slider)`

Slider that jumps to the click position (not just drag-only).

### `PlayerControls(QWidget)`

**Signals:**

| Signal | Type | Description |
|--------|------|-------------|
| `play_pause_clicked` | `()` | Play/Pause button clicked |
| `seek_requested` | `(float)` | Slider moved (value in seconds) |
| `open_requested` | `()` | Open button clicked |

**Public methods:**

| Method | Description |
|--------|-------------|
| `set_duration(duration: float)` | Set duration and unlock controls |
| `update_position(position: float)` | Update slider position and time label |
| `set_playing_state(is_playing: bool)` | Change icon Play ↔ Pause |

> **Note:** Controls (Play, Slider, Tracks) are disabled (`setEnabled(False)`) until a file is loaded.

---

## `ui/components/tracks_panel.py` — Mixer Panel

### `TracksPanel(QFrame)`

Floating panel (Tool Window) for managing audio tracks.

**Signals:**

| Signal | Type | Description |
|--------|------|-------------|
| `mix_changed` | `(list[MixSelection])` | Mix changed (enable/disable/volume) |
| `master_volume_changed` | `(int)` | Master volume changed (0–100) |

**Public methods:**

| Method | Description |
|--------|-------------|
| `set_tracks(tracks: list[Track])` | Populate the panel with track rows |

---

## `ui/components/track_row.py` — Track Row

### `TrackRow(SimpleCardWidget)`

Card for an individual audio track with checkbox and volume slider.

**Signals:**
- `state_changed()` — any state change (volume/enabled)

**Public methods:**
- `get_selection() -> MixSelection` — current track state

---

## `ui/components/history_panel.py` — History Panel

### `HistoryPanel(QFrame)`

List of recently opened files with double-click to open.

**Signals:**
- `file_selected(str)` — double-click on a list item

**Public methods:**
- `reload_history()` — reload list from DB
