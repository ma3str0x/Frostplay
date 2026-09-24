from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import SimpleCardWidget, SubtitleLabel, BodyLabel, LineEdit, PushButton, FluentIcon

from core.config import load_config, save_config


class SettingsPanel(SimpleCardWidget):  # type: ignore[misc]
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.config = load_config()
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(20, 20, 20, 20)
        self.v_layout.setSpacing(16)
        
        title = SubtitleLabel("Settings", self)
        
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
        
        self.v_layout.addWidget(title)
        self.v_layout.addLayout(folder_layout)
        self.v_layout.addStretch(1)

    def _on_browse_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Default Video Folder", 
            self.config.default_folder or ""
        )
        if folder:
            self.folder_edit.setText(folder)
            
    def _on_folder_edited(self, text: str) -> None:
        self.config.default_folder = text
        save_config(self.config)
