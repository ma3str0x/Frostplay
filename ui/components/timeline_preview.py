from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class TimelinePreview(QWidget):
    """Floating preview thumbnail card displayed above timeline on hover."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.setFixedSize(184, 134)
        self.current_seconds = -1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 6)
        layout.setSpacing(4)

        self.thumb_label = QLabel(self)
        self.thumb_label.setFixedSize(176, 99)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet(
            "background-color: #111111; border-radius: 6px; color: rgba(255, 255, 255, 0.4);"
        )

        self.time_label = QLabel("00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet(
            "color: #ffffff; font-size: 11px; font-weight: 600; background: transparent;"
        )

        layout.addWidget(self.thumb_label)
        layout.addWidget(self.time_label)

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 8.0, 8.0)

        # Card dark background with subtle border
        painter.fillPath(path, QColor(24, 24, 27, 240))
        painter.setPen(QColor(255, 255, 255, 30))
        painter.drawPath(path)

    def set_preview(self, seconds: float, pixmap: QPixmap | None) -> None:
        self.current_seconds = seconds
        self.time_label.setText(self._format_time(seconds))
        if pixmap and not pixmap.isNull():
            rounded = self._round_pixmap(pixmap, 176, 99, 6)
            self.thumb_label.setPixmap(rounded)
        else:
            self.thumb_label.clear()
            self.thumb_label.setText("Loading...")

    def update_pixmap_if_matching(self, sec: int, pixmap: QPixmap) -> None:
        if abs(self.current_seconds - sec) <= 1.5:
            rounded = self._round_pixmap(pixmap, 176, 99, 6)
            self.thumb_label.setPixmap(rounded)

    def position_above(self, slider: QWidget, x_in_slider: int) -> None:
        global_pos = slider.mapToGlobal(QPoint(x_in_slider, 0))
        desired_x = global_pos.x() - (self.width() // 2)
        desired_y = global_pos.y() - self.height() - 10

        # Clamp within available screen geometry
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            desired_x = max(geo.left() + 10, min(desired_x, geo.right() - self.width() - 10))
            desired_y = max(geo.top() + 10, desired_y)

        self.move(desired_x, desired_y)
        if not self.isVisible():
            self.show()

    def _round_pixmap(self, src: QPixmap, w: int, h: int, radius: int) -> QPixmap:
        scaled = src.scaled(
            w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        # Center-crop to exact dimensions
        crop_x = (scaled.width() - w) // 2
        crop_y = (scaled.height() - h) // 2
        cropped = scaled.copy(crop_x, crop_y, w, h)

        target = QPixmap(w, h)
        target.fill(Qt.GlobalColor.transparent)
        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)
        painter.end()
        return target

    def _format_time(self, seconds: float) -> str:
        sec_int = max(0, int(round(seconds)))
        hours = sec_int // 3600
        mins = (sec_int % 3600) // 60
        secs = sec_int % 60
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
