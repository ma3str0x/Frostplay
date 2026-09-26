from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    FluentIcon,
    LineEdit,
    PushButton,
    SimpleCardWidget,
    SubtitleLabel,
)

from core.config import load_config, save_config


class SettingsPanel(SimpleCardWidget):  # type: ignore[misc]
    history_preview_changed = pyqtSignal(bool)
    volume_boost_changed = pyqtSignal(bool)
    wheel_volume_changed = pyqtSignal(bool)
    blanket_fill_changed = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = load_config()

        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(24, 24, 24, 24)
        self.v_layout.setSpacing(18)

        title = SubtitleLabel("Settings", self)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        # Default folder setting
        folder_layout = QHBoxLayout()
        self.folder_label = BodyLabel("Default Video Folder:", self)

        self.folder_edit = LineEdit(self)
        self.folder_edit.setText(self.config.default_folder or "")
        self.folder_edit.setPlaceholderText("Select a folder...")
        self.folder_edit.textChanged.connect(self._on_folder_edited)

        self.browse_btn = PushButton(FluentIcon.FOLDER, "Browse", self)
        self.browse_btn.clicked.connect(self._on_browse_clicked)

        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_edit, 1)
        folder_layout.addWidget(self.browse_btn)

        # History previews checkbox
        self.preview_checkbox = CheckBox("Show video previews in history", self)
        self.preview_checkbox.setChecked(self.config.show_history_thumbnails)
        self.preview_checkbox.stateChanged.connect(self._on_preview_toggled)

        # Mouse wheel volume checkbox
        self.wheel_vol_checkbox = CheckBox("Control volume with mouse wheel", self)
        self.wheel_vol_checkbox.setChecked(self.config.wheel_volume_control)
        self.wheel_vol_checkbox.stateChanged.connect(self._on_wheel_vol_toggled)

        # 200% volume boost checkbox
        self.vol_boost_checkbox = CheckBox("Allow volume boost up to 200%", self)
        self.vol_boost_checkbox.setChecked(self.config.allow_volume_200)
        self.vol_boost_checkbox.stateChanged.connect(self._on_vol_boost_toggled)

        # Blanket fill checkbox
        self.blanket_fill_checkbox = CheckBox("Blanket Fill", self)
        self.blanket_fill_checkbox.setChecked(self.config.blanket_fill)
        self.blanket_fill_checkbox.stateChanged.connect(self._on_blanket_fill_toggled)

        self.v_layout.addWidget(title)
        self.v_layout.addLayout(folder_layout)
        self.v_layout.addWidget(self.preview_checkbox)
        self.v_layout.addWidget(self.wheel_vol_checkbox)
        self.v_layout.addWidget(self.vol_boost_checkbox)
        self.v_layout.addWidget(self.blanket_fill_checkbox)
        self.v_layout.addStretch(1)

    def _on_browse_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Default Video Folder",
            self.config.default_folder or "",
        )
        if folder:
            self.folder_edit.setText(folder)

    def _on_folder_edited(self, text: str) -> None:
        self.config.default_folder = text
        save_config(self.config)

    def _on_preview_toggled(self) -> None:
        val = self.preview_checkbox.isChecked()
        self.config.show_history_thumbnails = val
        save_config(self.config)
        self.history_preview_changed.emit(val)

    def _on_wheel_vol_toggled(self) -> None:
        val = self.wheel_vol_checkbox.isChecked()
        self.config.wheel_volume_control = val
        save_config(self.config)
        self.wheel_volume_changed.emit(val)

    def _on_vol_boost_toggled(self) -> None:
        val = self.vol_boost_checkbox.isChecked()
        self.config.allow_volume_200 = val
        save_config(self.config)
        self.volume_boost_changed.emit(val)

    def _on_blanket_fill_toggled(self) -> None:
        val = self.blanket_fill_checkbox.isChecked()
        self.config.blanket_fill = val
        save_config(self.config)
        self.blanket_fill_changed.emit(val)
