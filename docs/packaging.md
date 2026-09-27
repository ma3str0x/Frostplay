# Packaging & Installation — Frostplay

Comprehensive guide for building, packaging the installer, and Windows system integration for Frostplay.

---

## 1. Build Pipeline Overview

The build process is automated using the [build.py](file:///d:/Projects/Frostplay/build.py) script. The pipeline executes three sequential stages:

```mermaid
graph LR
    A["Frostplay_logo.png"] -->|build.py [1/3]| B["Frostplay.ico (256x256)"]
    B -->|build.py [2/3]| C["PyInstaller (frostplay.spec)"]
    C -->|Output: dist/Frostplay| D["Inno Setup (installer.iss)"]
    D -->|Output: dist_installer| E["Frostplay_Setup_v1.0.0.exe"]
```

1. **Application Icon Generation:**  
   If `img/Frostplay.ico` is missing, the script generates a square 256×256 ICO file from `img/Frostplay_logo.png` using high-quality anti-aliasing (`SmoothTransformation`).
2. **PyInstaller Compilation:**  
   Uses [frostplay.spec](file:///d:/Projects/Frostplay/frostplay.spec) in `--onedir` mode (`exclude_binaries=True`), bundling `mpv-2.dll`, `ffprobe.exe`, and the `img/` assets directory. The output is placed in `dist/Frostplay/`.
3. **Inno Setup Installer Compilation:**  
   Locates `ISCC.exe` in standard directories or the system `PATH`, compiling the final installer into `dist_installer/Frostplay_Setup_v1.0.0.exe`.
4. **Auto-update Installed Version (Dev):**  
   If `D:\Frostplay` exists on the development machine with `Frostplay.exe`, `build.py` automatically synchronizes the new binaries directly, eliminating the need to run the installer manually during development.

---

## 2. Quick Start Build

Prerequisites:
- Python 3.11+ virtual environment (`.venv`) with dependencies installed (`pip install -r requirements.txt pyinstaller`).
- Binary files in project root: [mpv-2.dll](file:///d:/Projects/Frostplay/mpv-2.dll) and [ffprobe.exe](file:///d:/Projects/Frostplay/ffprobe.exe).
- [Inno Setup 6](https://jrsoftware.org/isdl.php) installed on the system.

Execute the build script:
```powershell
python build.py
```

---

## 3. PyInstaller Specification (`frostplay.spec`)

- **Windowed GUI Mode:** `console=False` (no terminal window).
- **UPX Compression:** Enabled (`upx=True`).
- **Included Binaries:**
  - `mpv-2.dll` (placed in the root of the application bundle)
  - `ffprobe.exe` (placed in the root of the application bundle)
- **Included Data:**
  - `img/` (application logos, icons, graphics)
- **Hidden Imports:**  
  `qfluentwidgets`, `PyQt6`, `PyQt6.QtCore`, `PyQt6.QtGui`, `PyQt6.QtWidgets`, `PyQt6.QtNetwork`, `mpv`, `win32api`.

> [!NOTE]
> In PyInstaller windowed mode (`console=False`), standard file streams `sys.stdout` and `sys.stderr` are `None`. In [main.py](file:///d:/Projects/Frostplay/main.py), they are redirected to `os.devnull` on startup to avoid MSVCRT pipe blocking and stream write exceptions.

---

## 4. Inno Setup Configuration (`installer.iss`)

The installer is built using Inno Setup 6 and tailored for modern Windows 10/11 standards:

### 4.1. Privileges & Installation Directories
- **PrivilegesRequired=lowest**: The installer does not require Administrator rights (UAC elevation) for normal installation, preventing permission conflicts with user files.
- **Default Directory:** `{autopf}\Frostplay` (resolves to `%LOCALAPPDATA%\Programs\Frostplay` for standard non-elevated user accounts).
- **Wizard Style:** `modern`, using `lzma2/ultra64` compression.
- **Language:** English (`Default.isl`).

### 4.2. Windows Explorer Integration
1. **Context Menu:**  
   Adds an *"Open with Frostplay"* entry to the file context menu in Windows Explorer:
   - Registry: `HKCU\Software\Classes\*\shell\Frostplay`
   - Command: `"{app}\Frostplay.exe" "%1"`
2. **Registration under "Open with" (SupportedTypes):**  
   Registers Frostplay as a supported video player:
   - Registry: `HKCU\Software\Classes\Applications\Frostplay.exe\SupportedTypes`
   - Supported extensions: `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.wmv`, `.flv`, `.ts`.
   - This allows users to select Frostplay from the Windows "Open with" menu without forcing it as the system-wide default video handler.
3. **Optional File Associations (`Tasks: associatefiles`):**  
   - Creates a `Frostplay.Video` ProgID under `HKCU\Software\Classes` and registers `OpenWithProgids` for supported media types.
   - The task description clearly conveys format association without misleading users about overriding system defaults.

---

## 5. Startup Behavior & Single Instance IPC

Frostplay operates in **Single Instance** mode:
1. On launch, the application checks for an active local socket named `frostplay_single_instance_ipc` (`QLocalServer` / `QLocalSocket`).
2. If another instance of Frostplay is already running:
   - The file path passed via command line arguments (e.g. from "Open with") is written to the IPC socket and transmitted to the primary process.
   - The second instance exits immediately.
   - The primary instance brings its window to the foreground (`raise_()`, `activateWindow()`) and plays the requested video without startup lag.
