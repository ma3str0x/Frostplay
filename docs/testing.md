# Testing — Frostplay

Testing strategy, fixtures, and instructions for writing new tests.

## Overview

| Tool | Purpose |
|------|---------|
| `pytest` | Testing framework |
| `pytest-qt` | PyQt6 component testing |
| `hypothesis` | Property-based testing |
| `unittest.mock` | Mocking external dependencies (mpv, subprocess) |

Configuration: `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
qt_api = "pyqt6"
```

---

## Running Tests

```bash
# All tests
python -m pytest -v

# Specific file
python -m pytest tests/test_mixer.py -v

# Specific test
python -m pytest tests/test_mixer.py::test_build_lavfi_complex_properties -v

# With coverage (requires pytest-cov)
python -m pytest --cov=core --cov=db --cov=ui -v
```

---

## Test Structure

```
tests/
├── __init__.py
├── fixtures/                # Test fixtures (media files, etc.)
├── test_mixer.py            # core/mixer.py — lavfi-complex builder
├── test_player.py           # core/player.py — MpvPlayer (with mocks)
├── test_track_inspector.py  # core/track_inspector.py — ffprobe parsing
├── test_tracks_panel.py     # UI: TracksPanel + TrackRow
├── test_history.py          # db/history.py — history CRUD
└── test_ui_smoke.py         # Smoke: MainWindow creates without crashing
```

---

## Testing Strategies by Module

### `core/mixer.py` — Pure Unit Tests

The `mixer.py` module is a pure function with no side effects. Tested directly:

```python
def test_build_lavfi_complex_properties():
    selections = [
        MixSelection(index=1, volume=0.8, enabled=True),
        MixSelection(index=2, volume=0.5, enabled=True),
    ]
    result = build_lavfi_complex(selections)
    assert "[ao]" in result
    assert "amix" in result
```

**Hypothesis** is used for property-based testing:
- Output always contains `[ao]`
- Empty input → `anullsrc[ao]`

### `core/player.py` — libmpv Mocks

`python-mpv` is mocked via `unittest.mock.patch`:

```python
@patch("core.player.mpv", create=True)
@patch("core.player.inspect_tracks")
def test_mpv_player_open(mock_inspect, mock_mpv):
    mock_inspect.return_value = [Track(1, "eng", "aac")]
    player = MpvPlayer(wid=12345)
    player.open("test.mkv")
    assert len(player.get_tracks()) == 1
```

**Important:** `volume_max="150"` is passed to the MPV constructor — tests must account for this.

### `core/track_inspector.py` — subprocess Mocks

`ffprobe` is mocked via `unittest.mock.patch("subprocess.run")`:

```python
@patch("core.track_inspector.subprocess.run")
def test_inspect_tracks_success(mock_run):
    mock_run.return_value.stdout = json.dumps({
        "streams": [
            {"codec_name": "aac", "tags": {"language": "eng"}},
        ]
    })
    tracks = inspect_tracks("test.mkv")
    assert len(tracks) == 1
```

Edge cases tested:
- ffprobe not found → `TrackInspectorError`
- Invalid file → `TrackInspectorError`
- Invalid JSON → `TrackInspectorError`
- Empty streams → empty list

### `db/history.py` — In-memory SQLite

```python
def test_add_and_get_history(tmp_path):
    db_path = str(tmp_path / "test.db")
    add_to_history("/path/to/file.mkv", db_path=db_path)
    history = get_history(db_path=db_path)
    assert "/path/to/file.mkv" in history
```

Uses pytest's `tmp_path` fixture for temporary DB files.

### UI Components — pytest-qt

```python
def test_track_row_signals_and_selection(qtbot):
    track = Track(index=1, language="eng", codec="aac")
    row = TrackRow(track)
    qtbot.addWidget(row)

    # Verify signal is emitted when slider changes
    with qtbot.waitSignal(row.state_changed):
        row.slider.setValue(50)

    assert row.get_selection().volume == 0.5
```

**Key patterns:**
- `qtbot.addWidget(widget)` — register for automatic cleanup
- `qtbot.waitSignal(signal)` — wait for signal with timeout
- Never create `QApplication` manually — pytest-qt does this automatically

### Smoke Test

Minimal test that the main window creates without crashing:

```python
def test_main_window_creation(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window is not None
    assert window.windowTitle() == "Frostplay"
```

---

## FakePlayer

For testing UI without real libmpv, `core/fake_player.py` exists:

```python
from core.fake_player import FakePlayer
from core.types import Track

fake = FakePlayer(tracks=[
    Track(index=1, language="eng", codec="aac"),
    Track(index=2, language="ukr", codec="ac3"),
])
fake.open("any_path.mkv")
fake.play_pause()  # is_playing = True
fake.seek(30.0)    # current_position = 30.0
```

Use `FakePlayer` when:
- Writing tests for UI components
- Developing on a machine without GPU/display
- Running on CI (GitHub Actions)

---

## CI

Tests run automatically on every push/PR via GitHub Actions (`.github/workflows/ci.yml`):

```yaml
- name: Run tests with pytest
  run: |
    sudo apt-get install -y xvfb libxkbcommon-x11-0 ...
    xvfb-run pytest tests/
```

**xvfb** provides a virtual display for PyQt6 on headless Linux.

---

## Writing New Tests

### Conventions

- File: `tests/test_{module_name}.py`
- Functions: `test_{what_is_being_tested}()`
- One assert per logical check (but multiple asserts per test is fine)

### Checklist

- [ ] Test is isolated (doesn't depend on other tests)
- [ ] External dependencies are mocked (mpv, subprocess, file I/O)
- [ ] Edge cases are covered (empty input, invalid data)
- [ ] `ruff check tests/` passes
- [ ] `mypy tests/` passes
