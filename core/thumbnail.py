import hashlib
import os
import shutil
import tempfile
import time

from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QImage

from core.config import get_app_dir

THUMBNAILS_DIR = os.path.join(get_app_dir(), "thumbnails")
os.makedirs(THUMBNAILS_DIR, exist_ok=True)


def get_thumbnail_path(video_path: str) -> str:
    h = hashlib.md5(os.path.abspath(video_path).encode("utf-8")).hexdigest()
    return os.path.join(THUMBNAILS_DIR, f"{h}.jpg")


def has_thumbnail(video_path: str) -> bool:
    return os.path.exists(get_thumbnail_path(video_path))


def generate_thumbnail_sync(video_path: str, target_width: int = 240) -> str | None:
    if not os.path.exists(video_path):
        return None
    thumb_path = get_thumbnail_path(video_path)
    if os.path.exists(thumb_path):
        return thumb_path

    tmp_dir = tempfile.mkdtemp(prefix="fp_thumb_")
    try:
        import mpv
        p = mpv.MPV(
            vo="image",
            vo_image_format="jpeg",
            vo_image_outdir=tmp_dir,
            frames=1,
            ao="null",
            start="1",
        )
        p.play(video_path)
        try:
            p.wait_until_playing()
            time.sleep(0.3)
        except Exception:
            pass
        p.terminate()

        out_file = os.path.join(tmp_dir, "00000001.jpg")
        if os.path.exists(out_file):
            img = QImage(out_file)
            if not img.isNull():
                scaled = img.scaledToWidth(target_width, Qt.TransformationMode.SmoothTransformation)
                scaled.save(thumb_path, "JPEG", 85)
            else:
                shutil.copyfile(out_file, thumb_path)
            return thumb_path
    except Exception:
        pass
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return None


class ThumbnailSignals(QObject):
    ready = pyqtSignal(str, str)


class ThumbnailWorker(QRunnable):
    def __init__(self, video_path: str, signals: ThumbnailSignals) -> None:
        super().__init__()
        self.video_path = video_path
        self.signals = signals

    def run(self) -> None:
        thumb = generate_thumbnail_sync(self.video_path)
        if thumb and os.path.exists(thumb):
            self.signals.ready.emit(self.video_path, thumb)


class ThumbnailManager(QObject):
    thumbnail_ready = pyqtSignal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._pending: set[str] = set()
        self._signals = ThumbnailSignals()
        self._signals.ready.connect(self._on_ready)

    def request_thumbnail(self, video_path: str) -> str | None:
        thumb = get_thumbnail_path(video_path)
        if os.path.exists(thumb):
            return thumb
        if video_path not in self._pending and os.path.exists(video_path):
            self._pending.add(video_path)
            worker = ThumbnailWorker(video_path, self._signals)
            self._pool.start(worker)
        return None

    def _on_ready(self, video_path: str, thumb_path: str) -> None:
        self._pending.discard(video_path)
        self.thumbnail_ready.emit(video_path, thumb_path)


_GLOBAL_THUMB_MANAGER: ThumbnailManager | None = None


def get_thumbnail_manager() -> ThumbnailManager:
    global _GLOBAL_THUMB_MANAGER
    if _GLOBAL_THUMB_MANAGER is None:
        _GLOBAL_THUMB_MANAGER = ThumbnailManager()
    return _GLOBAL_THUMB_MANAGER
