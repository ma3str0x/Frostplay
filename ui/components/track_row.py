from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    FluentIcon,
    IconWidget,
    SimpleCardWidget,
    Slider,
)

from core.types import MixSelection, Track


class TrackRow(SimpleCardWidget):  # type: ignore
    state_changed = pyqtSignal()

    def __init__(self, track: Track, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.track = track

        # Top row elements
        self.checkbox = CheckBox()
        self.checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self._on_state_changed)

        self.icon = IconWidget(FluentIcon.MUSIC)
        self.icon.setFixedSize(16, 16)

        track_label = f"Track {track.index}"
        lang = track.language or 'und'
        codec = track.codec or 'aac'
        self.label = BodyLabel(f"{track_label} ({lang.lower()}, {codec.lower()})")

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.checkbox)
        top_layout.addWidget(self.icon)
        top_layout.addWidget(self.label)
        top_layout.addStretch(1)

        # Bottom row elements
        self.vol_icon = IconWidget(FluentIcon.VOLUME)
        self.vol_icon.setFixedSize(14, 14)

        self.slider = Slider(Qt.Orientation.Horizontal)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self._on_slider_changed)

        self.percent_label = CaptionLabel("100%")
        self.percent_label.setFixedWidth(35)
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        bottom_layout.addWidget(self.vol_icon)
        bottom_layout.addWidget(self.slider)
        bottom_layout.addWidget(self.percent_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        layout.addLayout(top_layout)
        layout.addLayout(bottom_layout)

        self._update_styles()

    def _on_slider_changed(self) -> None:
        self.percent_label.setText(f"{self.slider.value()}%")
        self.state_changed.emit()

    def _on_state_changed(self) -> None:
        self._update_styles()
        self.state_changed.emit()

    def _update_styles(self) -> None:
        is_on = self.checkbox.isChecked()
        self.slider.setEnabled(is_on)

        style = "" if is_on else "color: #888888;"
        self.label.setStyleSheet(style)
        self.percent_label.setStyleSheet(style)
        self.percent_label.setText(f"{self.slider.value()}%" if is_on else "Off")

    def get_selection(self) -> MixSelection:
        return MixSelection(
            index=self.track.index,
            volume=self.slider.value() / 100.0,
            enabled=self.checkbox.isChecked(),
        )
