from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from qfluentwidgets import FluentIcon, IconWidget


class PlayerWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e;")
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.v_layout.setSpacing(20)
        
        self.icon_widget = IconWidget(FluentIcon.VIDEO)
        self.icon_widget.setFixedSize(64, 64)
        
        self.label = QLabel("Frostplay")
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setStyleSheet("color: #888888;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.sub_label = QLabel("Open a video file to start playing")
        self.sub_label.setStyleSheet("color: #666666; font-size: 14px;")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.v_layout.addWidget(self.icon_widget, 0, Qt.AlignmentFlag.AlignHCenter)
        self.v_layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.v_layout.addWidget(self.sub_label, 0, Qt.AlignmentFlag.AlignHCenter)

    def hide_placeholder(self) -> None:
        self.icon_widget.hide()
        self.label.hide()
        self.sub_label.hide()

    def show_placeholder(self) -> None:
        self.icon_widget.show()
        self.label.show()
        self.sub_label.show()

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
