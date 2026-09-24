from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import FluentIcon, IconWidget, TitleLabel, BodyLabel


class PlayerWidget(QWidget):
    clicked = pyqtSignal()
    doubleClicked = pyqtSignal()
    open_requested = pyqtSignal()
    file_dropped = pyqtSignal(str)
    video_aspect_ratio_changed = pyqtSignal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PlayerWidget")
        self.setStyleSheet("#PlayerWidget { background-color: transparent; }")
        self.setAcceptDrops(True)
        self._is_empty = True
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.v_layout.setSpacing(16)
        
        self.icon_widget = IconWidget(FluentIcon.VIDEO)
        self.icon_widget.setFixedSize(64, 64)
        
        self.label = TitleLabel("Frostplay")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.sub_label = BodyLabel("Open a video file to start playing")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("color: rgba(255, 255, 255, 0.5);")
        
        self.v_layout.addWidget(self.icon_widget, 0, Qt.AlignmentFlag.AlignHCenter)
        self.v_layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.v_layout.addWidget(self.sub_label, 0, Qt.AlignmentFlag.AlignHCenter)

    def hide_placeholder(self) -> None:
        self._is_empty = False
        self.setStyleSheet("#PlayerWidget { background-color: black; }")
        self.icon_widget.hide()
        self.label.hide()
        self.sub_label.hide()

    def show_placeholder(self) -> None:
        self._is_empty = True
        self.setStyleSheet("#PlayerWidget { background-color: transparent; }")
        self.icon_widget.show()
        self.label.show()
        self.sub_label.show()

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            if self._is_empty:
                self.open_requested.emit()
            else:
                self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        if event is not None and event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent | None) -> None:
        if event is not None and event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                filepath = urls[0].toLocalFile()
                if filepath:
                    self.file_dropped.emit(filepath)
            event.acceptProposedAction()
