<div align="center">

<img src="img/Frostplay_logo.png" alt="Frostplay Logo" width="128" height="128">

# Frostplay

**A lightweight Windows video player.**  
Built with Python 3.11+, PyQt6, and libmpv.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](#)

[Download](#download--installation) • [Features](#features) • [Shortcuts](#shortcuts) • [Building from Source](#building-from-source) • [Documentation](#documentation)

---

</div>

## Overview

Frostplay allows playing video files while listening to multiple audio tracks at the same time. 

## Features

- **Multi-Track Audio Mixing:** Enable multiple audio tracks simultaneously with individual volume sliders.
- **Master Volume Control:** Smooth slider with optional boost up to 200% and mouse wheel support.
- **Timeline Previews:** Hover over the timeline to preview video frames.
- **Recent Files:** Fast history panel with video thumbnails and instant playback.
- **Fast Startup:** Instant launch via Single-Instance IPC without UI blocking.
- **Windows 11 UI:** Native dark theme with Mica background and fluid window resizing.
- **Broad Format Support:** Plays MP4, MKV, AVI, MOV, WebM, FLV, TS, and more via libmpv.

## Download & Installation

1. Go to the [Releases](https://github.com/ma3str0x/Frostplay/releases) page.
2. Download the latest installer (`Frostplay_Setup_vX.X.X.exe`).
3. Run the installer.

## Shortcuts

| Shortcut | Action |
|:---|:---|
| Space | Play / Pause |
| Left / Right | Seek backward / forward 10 seconds |
| F / Double Click | Toggle Fullscreen |
| C | Toggle Crop (Panscan fill vs. original aspect) |
| B | Toggle Blanket Fill (ambient blur) |
| Ctrl + I | Media properties |
| Scroll Wheel | Adjust master volume |

## Building from Source

### Prerequisites
- Python 3.11+
- Inno Setup 6 (optional, needed only to compile the installer via `build.py`)
- Binary dependencies in the project root (`mpv-2.dll`, `ffprobe.exe`):
  - Run `python setup_binaries.py` to auto-fetch binaries, or:
  - Manually place `mpv-2.dll` and `ffprobe.exe` in the project root directory.

### Setup & Run
```powershell
# Clone repository
git clone https://github.com/ma3str0x/Frostplay.git
cd Frostplay

# Setup virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run
python main.py
```

### Build Executable & Installer
```powershell
python build.py
```
Output files are saved to `dist/Frostplay/` and `dist_installer/`.

## Documentation

- [Architecture](docs/architecture.md) — structure, async track loading, and IPC flow.
- [API Reference](docs/api-reference.md) — classes, methods, and signals.
- [Packaging & Setup](docs/packaging.md) — build script and installer details.
- [UI Components](docs/ui-components.md) — interface controls and layout.
- [Testing](docs/testing.md) — unit tests and mock strategies.
- [Contributing](CONTRIBUTING.md) — code style and guidelines.

## License

GNU General Public License v3.0 (GPL-3.0). See [LICENSE](LICENSE) for details.

Copyright (C) 2026 **ma3str0** ([@ma3str0x](https://github.com/ma3str0x))
