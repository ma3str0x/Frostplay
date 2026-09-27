# Architecture — Frostplay

## Overview

Frostplay is built following **clean architecture** principles with a clear separation into three layers: **core** (business logic), **db** (persistence), **ui** (presentation). Each layer is isolated and communicates through well-defined contracts.

## Project Structure

```
Frostplay/
├── main.py                      # Entry point
├── pyproject.toml               # ruff, mypy, pytest configuration
├── requirements.txt             # Dependencies
├── config.example.json          # Example configuration
├── mpv-2.dll                    # libmpv library (Windows)
├── ffprobe.exe                  # FFprobe utility (Windows)
│
├── core/                        # Business logic (no UI dependencies)
│   ├── types.py                 # Shared types: Track, MixSelection, MixPreset
│   ├── player_interface.py      # ABC player interface
│   ├── player.py                # Real implementation via python-mpv
│   ├── fake_player.py           # Test implementation without libmpv
│   ├── mixer.py                 # Builds lavfi-complex string for audio mixing
│   ├── track_inspector.py       # Extracts audio tracks via ffprobe
│   └── config.py                # Loads configuration from JSON
│
├── db/                          # Persistence layer (SQLite)
│   ├── schema.py                # DB schema initialization and migration
│   └── history.py               # CRUD for the history table
│
├── ui/                          # Presentation layer (PyQt6 + QFluentWidgets)
│   ├── main_window.py           # Main window, navigation, orchestration
│   ├── player_widget.py         # Video rendering widget (mpv wid)
│   └── components/              # Reusable UI components
│       ├── player_controls.py   # Play/pause, slider, time, buttons
│       ├── tracks_panel.py      # Floating audio mixer panel
│       ├── track_row.py         # Individual track row with volume slider
│       └── history_panel.py     # Recently opened files panel
│
├── tests/                       # Tests (pytest + pytest-qt)
│   ├── fixtures/                # Test fixtures
│   ├── test_mixer.py            # lavfi-complex builder tests
│   ├── test_player.py           # MpvPlayer tests (with mocks)
│   ├── test_track_inspector.py  # ffprobe parsing tests
│   ├── test_tracks_panel.py     # Mixer UI component tests
│   ├── test_history.py          # History CRUD tests
│   └── test_ui_smoke.py         # Smoke test for main window creation
│
├── docs/                        # Documentation
└── .github/workflows/ci.yml     # GitHub Actions CI pipeline
```

## Dependency Diagram

```mermaid
graph TB
    main["main.py<br/>(Entry Point)"]
    
    subgraph core["core/ — Business Logic"]
        types["types.py<br/>Track, MixSelection"]
        player_iface["player_interface.py<br/>PlayerInterface ABC"]
        player["player.py<br/>MpvPlayer"]
        fake_player["fake_player.py<br/>FakePlayer"]
        mixer["mixer.py<br/>build_lavfi_complex()"]
        inspector["track_inspector.py<br/>inspect_tracks()"]
        config["config.py<br/>Config, load_config()"]
    end
    
    subgraph db["db/ — Persistence"]
        schema["schema.py<br/>init_db()"]
        history["history.py<br/>add_to_history(), get_history()"]
    end
    
    subgraph ui["ui/ — Presentation"]
        main_window["main_window.py<br/>MainWindow"]
        player_widget["player_widget.py<br/>PlayerWidget"]
        controls["player_controls.py<br/>PlayerControls"]
        tracks_panel["tracks_panel.py<br/>TracksPanel"]
        track_row["track_row.py<br/>TrackRow"]
        history_panel["history_panel.py<br/>HistoryPanel"]
    end
    
    main --> main_window
    main --> schema
    
    main_window --> player
    main_window --> mixer
    main_window --> history
    main_window --> player_widget
    main_window --> controls
    main_window --> tracks_panel
    main_window --> history_panel
    
    player --> player_iface
    player --> inspector
    player --> types
    fake_player --> player_iface
    fake_player --> types
    mixer --> types
    inspector --> types
    
    tracks_panel --> track_row
    tracks_panel --> types
    track_row --> types
    history_panel --> history
    history --> schema
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant MainWindow
    participant MpvPlayer
    participant libmpv
    participant TracksPanel
    participant Mixer

    User->>MainWindow: Open file (GUI or "Open with")
    MainWindow->>MpvPlayer: open(filepath)
    MpvPlayer->>libmpv: play(filepath) [Immediate non-blocking]
    libmpv-->>MpvPlayer: property_observer("track-list") fires
    MpvPlayer-->>MainWindow: tracks_callback(list[Track])
    MainWindow->>TracksPanel: set_tracks(tracks)
    TracksPanel-->>MainWindow: mix_changed(list[MixSelection])
    MainWindow->>Mixer: build_lavfi_complex(selections)
    Mixer-->>MainWindow: lavfi_str
    MainWindow->>MpvPlayer: set_mix(lavfi_str)
```

## Key Architectural Decisions

### 1. Player Interface (Strategy Pattern)

`PlayerInterface` is an abstract base class that defines the player contract. Two implementations:

- **`MpvPlayer`** — real player via python-mpv + libmpv
- **`FakePlayer`** — test stub for CI and unit tests without GPU/display

This allows developing and testing the UI without a real video file.

### 2. Deferred MPV Initialization & Async Property Observers

- MPV is initialized only after `showEvent()` of the main window via `QTimer.singleShot(0, ...)` to guarantee that `winId()` is already valid (native window has been created).
- **Asynchronous Track Extraction:** Instead of synchronously spawning external `ffprobe` processes during `open()` (which previously caused 5-7 second UI freezes), `MpvPlayer` listens to `libmpv`'s native `track-list` property observer. Audio tracks are parsed on-the-fly and delivered to the UI without blocking the Qt event loop.

### 3. Single-Instance IPC Architecture

Frostplay uses `QLocalServer` / `QLocalSocket` for cross-process communication. When a user double-clicks a video or uses "Open with" while Frostplay is already running, the new process sends the file path over the IPC channel to the primary instance and terminates immediately, eliminating redundant process startup overhead.

### 4. Floating Panel (Tool Window)

`TracksPanel` uses `Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint`:
- Does not block the main window (unlike `Dialog`/`Popup`)
- Can be dragged with the mouse
- Displayed above the player

### 5. lavfi-complex Mixing

Audio track mixing happens at the libmpv level through the `lavfi-complex` filter graph. The `mixer.py` module builds the filter string in a purely functional manner, without side effects.

### 6. Lazy Loading for Heavy UI Components

The `HistoryPanel` defers heavy item population until the user actually switches to the History tab, preventing unnecessary widget creation and disk access during initial application launch.


## External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| PyQt6 | ≥6.6.0 | GUI framework |
| PyQt6-Fluent-Widgets | ≥1.5.0 | Fluent Design components |
| python-mpv | ≥1.0.5 | libmpv bindings |
| mpv-2.dll | — | Video rendering (Windows) |
| ffprobe | — | Audio track analysis |

## Binary Dependencies

On Windows, `mpv-2.dll` and `ffprobe.exe` must be placed in the project root directory. `main.py` automatically adds the current directory to `PATH` and calls `os.add_dll_directory()` for proper DLL loading.
