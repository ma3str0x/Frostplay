from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget
from qfluentwidgets import FluentIcon, IconWidget


class VolumeIndicator(QWidget):
    """Sleek on-screen display (OSD) volume pill in top-right corner without corner artifacts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("VolumeIndicator")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 16, 8)
        layout.setSpacing(8)

        self.icon_widget = IconWidget(self)
        self.icon_widget.setFixedSize(20, 20)

        self.label = QLabel("100%", self)
        self.label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600; background: transparent;")

        layout.addWidget(self.icon_widget)
        layout.addWidget(self.label)

        # Native window opacity animation (no offscreen pixmap artifacts)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(220)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._fade_anim.finished.connect(self._on_fade_finished)

        # Hide timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(1200)
        self._timer.timeout.connect(self._fade_out)

        self.hide()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2.0

        path = QPainterPath()
        path.addRoundedRect(
            float(rect.x()),
            float(rect.y()),
            float(rect.width()),
            float(rect.height()),
            radius,
            radius,
        )

        # Draw anti-aliased dark capsule
        painter.fillPath(path, QColor(24, 24, 24, 230))
        painter.setPen(QColor(255, 255, 255, 40))
        painter.drawPath(path)

    def show_volume(self, volume: int, anchor_widget: QWidget | None = None) -> None:
        white = QColor(255, 255, 255)
        if volume == 0:
            self.icon_widget.setIcon(FluentIcon.MUTE.icon(color=white))
        else:
            self.icon_widget.setIcon(FluentIcon.VOLUME.icon(color=white))

        self.label.setText(f"{volume}%")
        self.adjustSize()

        if anchor_widget:
            top_right = anchor_widget.mapToGlobal(QPoint(anchor_widget.width(), 0))
            x = top_right.x() - self.width() - 24
            y = top_right.y() + 20
            self.move(x, y)

        self._fade_anim.stop()
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()

        self._timer.start()

    def show_message(self, text: str, icon: FluentIcon = FluentIcon.VIEW, anchor_widget: QWidget | None = None) -> None:
        white = QColor(255, 255, 255)
        self.icon_widget.setIcon(icon.icon(color=white))
        self.label.setText(text)
        self.adjustSize()

        if anchor_widget:
            top_right = anchor_widget.mapToGlobal(QPoint(anchor_widget.width(), 0))
            x = top_right.x() - self.width() - 24
            y = top_right.y() + 20
            self.move(x, y)

        self._fade_anim.stop()
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()

        self._timer.start()

    def _fade_out(self) -> None:
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        if self.windowOpacity() == 0.0:
            self.hide()
