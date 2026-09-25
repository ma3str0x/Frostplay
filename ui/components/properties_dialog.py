import os
import subprocess

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import FluentIcon, PushButton, SubtitleLabel, TransparentToolButton

from core.media_properties import MediaProperties


class PropertiesDialog(QDialog):
    """Modern Windows Media Player-style Properties dialog."""

    def __init__(self, properties: MediaProperties, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.properties = properties
        self._drag_pos = QPoint()

        # Frameless dialog
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(540)

        self._init_ui()
        self._center_on_parent(parent)

    def _init_ui(self) -> None:
        # Outer container for dark rounded background and subtle border
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        self.card = QWidget(self)
        self.card.setObjectName("propertiesCard")
        self.card.setStyleSheet("""
            QWidget#propertiesCard {
                background-color: #202020;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        # Header: Title + Close 'X' button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = SubtitleLabel("Properties", self.card)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        btn_x = TransparentToolButton(FluentIcon.CLOSE, self.card)
        btn_x.setFixedSize(30, 30)
        btn_x.clicked.connect(self.accept)
        header_layout.addWidget(btn_x)

        card_layout.addLayout(header_layout)

        # 2-column grid layout for fields
        grid = QGridLayout()
        grid.setHorizontalSpacing(32)
        grid.setVerticalSpacing(14)
        grid.setContentsMargins(0, 4, 0, 4)

        # Row 0: Title & Subtitle
        grid.addLayout(self._create_field("Title", self.properties.title), 0, 0)
        grid.addLayout(self._create_field("Subtitle", self.properties.subtitle), 0, 1)

        # Row 1: Contributing artists & Length
        grid.addLayout(self._create_field("Contributing artists", self.properties.artists), 1, 0)
        grid.addLayout(self._create_field("Length", self.properties.length), 1, 1)

        # Row 2: Genre & Year
        grid.addLayout(self._create_field("Genre", self.properties.genre), 2, 0)
        grid.addLayout(self._create_field("Year", self.properties.year), 2, 1)

        # Row 3: Resolution & Frame rate
        grid.addLayout(self._create_field("Resolution", self.properties.resolution), 3, 0)
        grid.addLayout(self._create_field("Frame rate", self.properties.frame_rate), 3, 1)

        # Row 4: Audio channels & Item type
        grid.addLayout(self._create_field("Audio channels", self.properties.audio_channels), 4, 0)
        grid.addLayout(self._create_field("Item type", self.properties.item_type), 4, 1)

        card_layout.addLayout(grid)

        # File location section (full width)
        loc_layout = QVBoxLayout()
        loc_layout.setSpacing(3)
        loc_layout.setContentsMargins(0, 4, 0, 2)

        loc_label = QLabel("File location", self.card)
        loc_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")

        loc_val = QLabel(self.properties.file_location, self.card)
        loc_val.setWordWrap(True)
        loc_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        loc_val.setStyleSheet("color: #ffffff; font-size: 13px; line-height: 1.3;")

        loc_layout.addWidget(loc_label)
        loc_layout.addWidget(loc_val)
        card_layout.addLayout(loc_layout)

        # 'Open file location' link button
        link_btn = QLabel("Open file location", self.card)
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.setStyleSheet(
            "color: #ea580c; font-size: 13px; font-weight: 500;"
            "margin-top: 2px; margin-bottom: 6px;"
        )
        link_btn.mousePressEvent = lambda e: self._on_open_location()  # type: ignore[assignment]
        card_layout.addWidget(link_btn)

        # Bottom buttons row: Close button on the right
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 10, 0, 0)
        btn_row.addStretch(1)

        self.btn_close = PushButton("Close", self.card)
        self.btn_close.setFixedWidth(110)
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)

        card_layout.addLayout(btn_row)
        outer_layout.addWidget(self.card)

    def _center_on_parent(self, parent: QWidget | None) -> None:
        if parent:
            geo = parent.geometry()
            self.adjustSize()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(max(0, x), max(0, y))

    def _create_field(self, label_text: str, value_text: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label_text, self.card)
        lbl.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")

        val = QLabel(value_text if value_text else "-", self.card)
        val.setWordWrap(True)
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        val.setStyleSheet("color: #ffffff; font-size: 14px;")

        layout.addWidget(lbl)
        layout.addWidget(val)
        return layout

    def _on_open_location(self) -> None:
        filepath = self.properties.file_location
        if filepath and os.path.exists(filepath):
            subprocess.Popen(f'explorer /select,"{os.path.normpath(filepath)}"')
        elif filepath and os.path.isdir(os.path.dirname(filepath)):
            subprocess.Popen(f'explorer "{os.path.normpath(os.path.dirname(filepath))}"')

    def mousePressEvent(self, e: QMouseEvent | None) -> None:
        if e and e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e: QMouseEvent | None) -> None:
        if e and e.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e: QMouseEvent | None) -> None:
        self._drag_pos = QPoint()

    def keyPressEvent(self, e: QKeyEvent | None) -> None:
        if e and e.key() == Qt.Key.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(e)
