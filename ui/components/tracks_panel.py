from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QStyle, QStyleOption
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon,
    IconWidget,
    Slider,
    SmoothScrollArea,
    SubtitleLabel,
    ToolButton,
)

from core.types import Track
from ui.components.track_row import TrackRow


class TracksPanel(QFrame):
    mix_changed = pyqtSignal(list)
    master_volume_changed = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("TracksPanel")
        self.setStyleSheet(
            "QFrame#TracksPanel { background-color: #2b2b2b; "
            "border: 1px solid #444; border-radius: 8px; }"
        )
        self.setMinimumWidth(420)
        self.setMaximumHeight(500)
        self._rows: list[TrackRow] = []

        title = SubtitleLabel("Audio Tracks")
        title.setContentsMargins(10, 10, 10, 0)

        self.btn_close = ToolButton(FluentIcon.CLOSE)
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_close.clicked.connect(self.hide)

        title_layout = QHBoxLayout()
        title_layout.addWidget(title)
        title_layout.addStretch(1)
        title_layout.addWidget(self.btn_close)

        # Master Volume row
        master_vol_layout = QHBoxLayout()
        master_vol_layout.setContentsMargins(15, 5, 15, 5)

        self.master_vol_icon = IconWidget(FluentIcon.VOLUME)
        self.master_vol_icon.setFixedSize(16, 16)

        self.master_vol_label = BodyLabel("Master Volume")

        self.master_vol_slider = Slider(Qt.Orientation.Horizontal)
        self.master_vol_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.master_vol_slider.setRange(0, 100)
        self.master_vol_slider.setValue(100)
        self.master_vol_slider.valueChanged.connect(self._on_master_vol_changed)

        self.master_vol_percent = CaptionLabel("100%")
        self.master_vol_percent.setFixedWidth(45)
        self.master_vol_percent.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )


        master_vol_layout.addWidget(self.master_vol_icon)
        master_vol_layout.addWidget(self.master_vol_label)
        master_vol_layout.addWidget(self.master_vol_slider)
        master_vol_layout.addWidget(self.master_vol_percent)

        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.scroll_widget = QFrame()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch(1)
        self.scroll_area.setWidget(self.scroll_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addLayout(title_layout)
        layout.addLayout(master_vol_layout)
        layout.addWidget(self.scroll_area)

        self._drag_pos: QPoint | None = None

    def paintEvent(self, event) -> None:
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        super().paintEvent(event)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        self._drag_pos = None
        if event is not None:
            event.accept()

    def _on_master_vol_changed(self) -> None:
        val = self.master_vol_slider.value()
        self.master_vol_percent.setText(f"{val}%")
        self.master_volume_changed.emit(val)

    def set_allow_volume_200(self, allowed: bool) -> None:
        max_val = 200 if allowed else 100
        self.master_vol_slider.setMaximum(max_val)
        if self.master_vol_slider.value() > max_val:
            self.master_vol_slider.setValue(max_val)


    def set_tracks(self, tracks: list[Track]) -> None:
        # Clear existing rows
        for row in self._rows:
            self.scroll_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

        # Add new rows
        for track in tracks:
            row = TrackRow(track)
            row.state_changed.connect(self._on_row_changed)
            self._rows.append(row)
            # Insert before the stretch
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, row)

        self._emit_mix()

    def _on_row_changed(self) -> None:
        self._emit_mix()

    def _emit_mix(self) -> None:
        selections = [row.get_selection() for row in self._rows]
        self.mix_changed.emit(selections)
