"""
Frostplay Automated Build & Packaging Script
Usage:
    python build.py
"""

import os
import shutil
import subprocess
import sys


def find_iscc() -> str | None:
    # Check PATH
    iscc = shutil.which("ISCC.exe") or shutil.which("iscc")
    if iscc:
        return iscc

    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"),
        os.path.expandvars(r"%ProgramFiles%\Inno Setup 6\ISCC.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def main() -> None:
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    print("=" * 60)
    print("Frostplay: Starting Automated Build Pipeline")
    print("=" * 60)

    # 1. Generate ICO if needed
    ico_path = os.path.join(project_dir, "img", "Frostplay.ico")
    png_path = os.path.join(project_dir, "img", "Frostplay_logo.png")
    if not os.path.exists(ico_path) and os.path.exists(png_path):
        print("[1/3] Generating Frostplay.ico from Frostplay_logo.png...")
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QImage
        img = QImage(png_path)
        size = min(img.width(), img.height())
        cropped = img.copy((img.width() - size) // 2, (img.height() - size) // 2, size, size)
        scaled = cropped.scaled(
            256,
            256,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.save(ico_path, "ICO")


    # 2. PyInstaller build
    print("[2/3] Running PyInstaller...")
    pyinstaller_exe = os.path.join(project_dir, ".venv", "Scripts", "pyinstaller.exe")
    if not os.path.exists(pyinstaller_exe):
        pyinstaller_exe = "pyinstaller"

    cmd_pyinstaller = [pyinstaller_exe, "frostplay.spec", "--clean", "-y"]
    res = subprocess.run(cmd_pyinstaller)
    if res.returncode != 0:
        print("ERROR: PyInstaller build failed!")
        sys.exit(res.returncode)

    # 3. Inno Setup compile
    print("[3/3] Compiling Inno Setup Installer...")
    iscc_path = find_iscc()
    if not iscc_path:
        print("WARNING: Inno Setup compiler (ISCC.exe) not found.")
        print("Standalone executable built in 'dist/Frostplay/Frostplay.exe'.")
        print("To build the installer, install Inno Setup 6 and run 'ISCC.exe installer.iss'.")
        return

    cmd_iscc = [iscc_path, "installer.iss"]
    res_iscc = subprocess.run(cmd_iscc)
    if res_iscc.returncode != 0:
        print("ERROR: Inno Setup compilation failed!")
        sys.exit(res_iscc.returncode)

    # 4. Optional: If Frostplay is installed in D:\Frostplay, update it directly
    install_target = r"D:\Frostplay"
    if os.path.isdir(install_target) and os.path.exists(os.path.join(install_target, "Frostplay.exe")):
        print(f"\n[4/4] Updating installed files in {install_target}...")
        try:
            dist_dir = os.path.join(project_dir, "dist", "Frostplay")
            for item in os.listdir(dist_dir):
                s = os.path.join(dist_dir, item)
                d = os.path.join(install_target, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            print(f"Successfully updated installed files in {install_target}!")
        except Exception as e:
            print(f"Notice: Could not auto-update {install_target}: {e}")

    print("\n" + "=" * 60)
    print("SUCCESS! Frostplay Setup Installer generated:")
    setup_file = os.path.join(project_dir, "dist_installer", "Frostplay_Setup_v1.0.0.exe")
    if os.path.exists(setup_file):
        print(f"Path: {setup_file} ({os.path.getsize(setup_file) / (1024*1024):.1f} MB)")
    print("=" * 60)


if __name__ == "__main__":
    main()
