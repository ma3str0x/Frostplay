import os
import shutil
import tempfile
import time
from typing import Any

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap


class _PreviewThread(QThread):
    frame_ready = pyqtSignal(int, QPixmap)

    def __init__(self, video_path: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.video_path = video_path
        self.tmp_dir = tempfile.mkdtemp(prefix="fp_prev_")
        self._target_sec: int | None = None
        self._running = True
        self._mpv: Any = None

    def run(self) -> None:
        try:
            import mpv

            self._mpv = mpv.MPV(
                vo="image",
                vo_image_format="jpeg",
                vo_image_outdir=self.tmp_dir,
                ao="null",
                pause=True,
                keep_open=True,
            )
            self._mpv.play(self.video_path)
            time.sleep(0.3)

            while self._running:
                if self._target_sec is not None:
                    sec = self._target_sec
                    self._target_sec = None
                    out_path = os.path.join(self.tmp_dir, f"frame_{sec}.jpg")
                    if not os.path.exists(out_path):
                        try:
                            self._mpv.seek(float(sec), "absolute+keyframes")
                            time.sleep(0.04)
                            self._mpv.command("screenshot-to-file", out_path, "video")
                        except Exception:
                            pass
                    if os.path.exists(out_path):
                        img = QImage(out_path)
                        if not img.isNull():
                            scaled = img.scaledToWidth(
                                180, Qt.TransformationMode.SmoothTransformation
                            )
                            pix = QPixmap.fromImage(scaled)
                            self.frame_ready.emit(sec, pix)
                time.sleep(0.02)
        except Exception:
            pass
        finally:
            if self._mpv:
                try:
                    self._mpv.terminate()
                except Exception:
                    pass
            self._cleanup_tmp()

    def request(self, sec: int) -> None:
        self._target_sec = sec

    def stop(self) -> None:
        self._running = False
        self.wait(1000)

    def _cleanup_tmp(self) -> None:
        if os.path.exists(self.tmp_dir):
            try:
                shutil.rmtree(self.tmp_dir, ignore_errors=True)
            except Exception:
                pass


class PreviewGenerator(QObject):
    frame_available = pyqtSignal(int, QPixmap)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: _PreviewThread | None = None
        self._cache: dict[int, QPixmap] = {}
        self._current_path: str | None = None

    def load_video(self, video_path: str) -> None:
        self.close()
        self._current_path = video_path
        self._cache.clear()
        if os.path.exists(video_path):
            self._worker = _PreviewThread(video_path, self)
            self._worker.frame_ready.connect(self._on_frame_ready)
            self._worker.start()

    def get_preview(self, seconds: float) -> QPixmap | None:
        sec = max(0, int(round(seconds)))
        if sec in self._cache:
            return self._cache[sec]

        # Return nearest frame if available within 3 seconds
        for offset in (1, -1, 2, -2, 3, -3):
            cand = sec + offset
            if cand in self._cache:
                if self._worker:
                    self._worker.request(sec)
                return self._cache[cand]

        if self._worker:
            self._worker.request(sec)
        return None

    def _on_frame_ready(self, sec: int, pix: QPixmap) -> None:
        # Keep cache bounded to 100 frames
        if len(self._cache) > 100:
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        self._cache[sec] = pix
        self.frame_available.emit(sec, pix)

    def close(self) -> None:
        if self._worker:
            self._worker.stop()
            self._worker = None
        self._cache.clear()
        self._current_path = None
