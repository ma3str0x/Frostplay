from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import BodyLabel, FluentIcon, Slider, ToolButton


class ClickableSlider(Slider):  # type: ignore[misc]
    def mousePressEvent(self, e: QMouseEvent | None) -> None:
        super().mousePressEvent(e)
        if e is not None and e.button() == Qt.MouseButton.LeftButton:
            x_pos = e.position().x()
            val = self.minimum() + ((self.maximum() - self.minimum()) * x_pos) / self.width()
            self.setValue(int(val))
            self.sliderMoved.emit(self.value())


class PlayerControls(QWidget):
    play_pause_clicked = pyqtSignal()
    seek_requested = pyqtSignal(float)
    open_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(50)

        self.btn_play = ToolButton(FluentIcon.PLAY)
        self.btn_play.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_play.setEnabled(False)
        self.btn_play.clicked.connect(self.play_pause_clicked)

        self.slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.setEnabled(False)
        self.slider.sliderMoved.connect(self._on_slider_moved)

        self.time_label = BodyLabel("00:00 / 00:00")

        self.btn_open = ToolButton(FluentIcon.FOLDER)
        self.btn_open.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_open.clicked.connect(self.open_requested)

        self.btn_tracks = ToolButton(FluentIcon.MUSIC)
        self.btn_tracks.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_tracks.setEnabled(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.addWidget(self.btn_play)
        layout.addWidget(self.slider)
        layout.addWidget(self.time_label)
        layout.addWidget(self.btn_tracks)
        layout.addWidget(self.btn_open)

        self._duration = 0.0

    def set_duration(self, duration: float) -> None:
        self._duration = duration
        self.slider.setRange(0, int(duration))
        is_loaded = duration > 0
        self.slider.setEnabled(is_loaded)
        self.btn_play.setEnabled(is_loaded)
        self.btn_tracks.setEnabled(is_loaded)

    def update_position(self, position: float) -> None:
        if not self.slider.isSliderDown():
            self.slider.setValue(int(position))
        fmt_pos = self._format_time(position)
        fmt_dur = self._format_time(self._duration)
        self.time_label.setText(f"{fmt_pos} / {fmt_dur}")

    def set_playing_state(self, is_playing: bool) -> None:
        icon = FluentIcon.PAUSE if is_playing else FluentIcon.PLAY
        self.btn_play.setIcon(icon)

    def _on_slider_moved(self, value: int) -> None:
        self.seek_requested.emit(float(value))

    def _format_time(self, seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
