from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout
from qfluentwidgets import ListWidget, SimpleCardWidget, TitleLabel, BodyLabel

from db.history import get_history


class HistoryPanel(SimpleCardWidget):  # type: ignore[misc]
    file_selected = pyqtSignal(str)

    def __init__(self, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("History")

        self.list_widget = ListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

        title = TitleLabel("Recent Files")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        subtitle = BodyLabel("Double click a file to play it again")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.5);")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        
        layout.addSpacing(12)
        layout.addWidget(self.list_widget)

        self.reload_history()

    def reload_history(self) -> None:
        self.list_widget.clear()
        paths = get_history()
        for path in paths:
            self.list_widget.addItem(path)

    def _on_item_double_clicked(self, item) -> None:  # type: ignore
        self.file_selected.emit(item.text())
