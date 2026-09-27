"""
Frostplay - Binary Dependencies Setup Script
Downloads and extracts mpv-2.dll and ffprobe.exe automatically.
"""

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MPV_TARGET = os.path.join(PROJECT_ROOT, "mpv-2.dll")
FFPROBE_TARGET = os.path.join(PROJECT_ROOT, "ffprobe.exe")

FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
MPV_API_URL = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"


def download_with_progress(url: str, dest_path: str, label: str) -> None:
    print(f"Downloading {label}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_file:
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        block_size = 1024 * 512
        while True:
            chunk = resp.read(block_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                percent = downloaded / total * 100
                mb_down = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                status = f"\r  [{percent:5.1f}%] {mb_down:.1f}MB / {mb_total:.1f}MB"
                print(status, end="", flush=True)
    print("\n  Download complete.")


def setup_ffprobe() -> None:
    if os.path.exists(FFPROBE_TARGET):
        print("[OK] ffprobe.exe already exists.")
        return

    temp_zip = os.path.join(PROJECT_ROOT, "_temp_ffmpeg.zip")
    try:
        download_with_progress(FFMPEG_ZIP_URL, temp_zip, "FFmpeg essentials")
        print("Extracting ffprobe.exe from archive...")
        with zipfile.ZipFile(temp_zip, "r") as z:
            for name in z.namelist():
                if name.endswith("bin/ffprobe.exe") or name.endswith("ffprobe.exe"):
                    with z.open(name) as src, open(FFPROBE_TARGET, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    print(f"[OK] Extracted: {FFPROBE_TARGET}")
                    break
    except Exception as e:
        print(f"[!] Failed to download FFmpeg: {e}")
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)


def get_latest_mpv_url() -> str | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = urllib.request.Request(MPV_API_URL, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            # Prefer standard x86_64 dev build
            if name.startswith("mpv-dev-x86_64-") and not name.startswith("mpv-dev-x86_64-v3-"):
                return str(asset.get("browser_download_url"))
        for asset in data.get("assets", []):
            if "mpv-dev" in asset.get("name", "") and "x86_64" in asset.get("name", ""):
                return str(asset.get("browser_download_url"))
    except Exception as e:
        print(f"[!] Could not query GitHub releases for libmpv: {e}")
    return None


def setup_mpv() -> None:
    if os.path.exists(MPV_TARGET):
        print("[OK] mpv-2.dll already exists.")
        return

    mpv_url = get_latest_mpv_url()
    if not mpv_url:
        print("[!] Could not resolve latest libmpv download URL.")
        return

    temp_7z = os.path.join(PROJECT_ROOT, "_temp_mpv.7z")
    temp_dir = tempfile.mkdtemp(prefix="mpv_extract_")
    try:
        download_with_progress(mpv_url, temp_7z, "libmpv Windows build")
        print("Extracting mpv-2.dll from archive...")
        # Windows 10/11 includes bsdtar which handles 7z natively
        cmd = ["tar", "-xf", temp_7z, "-C", temp_dir]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode == 0:
            found = False
            for root, _, files in os.walk(temp_dir):
                for f in files:
                    if f.lower() in ("mpv-2.dll", "libmpv-2.dll"):
                        src_path = os.path.join(root, f)
                        shutil.copy2(src_path, MPV_TARGET)
                        print(f"[OK] Extracted: {MPV_TARGET}")
                        found = True
                        break
                if found:
                    break
            if not found:
                print("[!] mpv-2.dll was not found inside the downloaded archive.")
        else:
            print(f"[!] Extraction with tar failed: {res.stderr.decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"[!] Failed to auto-download libmpv: {e}")
    finally:
        if os.path.exists(temp_7z):
            os.remove(temp_7z)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def check_status() -> None:
    print("\nDependency status:")
    print(f"  mpv-2.dll:   {'[FOUND]' if os.path.exists(MPV_TARGET) else '[MISSING]'}")
    print(f"  ffprobe.exe: {'[FOUND]' if os.path.exists(FFPROBE_TARGET) else '[MISSING]'}")


def main() -> None:
    print("=" * 60)
    print("Frostplay: Automated Binary Dependencies Setup")
    print("=" * 60)

    setup_ffprobe()
    setup_mpv()
    check_status()


if __name__ == "__main__":
    main()
