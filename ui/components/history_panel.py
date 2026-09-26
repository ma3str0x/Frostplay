import os

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon,
    ListWidget,
    SimpleCardWidget,
    TitleLabel,
)

from core.config import load_config
from core.thumbnail import get_thumbnail_manager, get_thumbnail_path, has_thumbnail
from db.history import get_history


def make_rounded_pixmap(
    pixmap: QPixmap, width: int = 100, height: int = 56, radius: int = 6
) -> QPixmap:
    target = QPixmap(width, height)
    target.fill(Qt.GlobalColor.transparent)
    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, width, height, radius, radius)
    painter.setClipPath(path)
    scaled = pixmap.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = (width - scaled.width()) // 2
    y = (height - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()
    return target


def create_placeholder_pixmap(width: int = 100, height: int = 56, radius: int = 6) -> QPixmap:
    target = QPixmap(width, height)
    target.fill(Qt.GlobalColor.transparent)
    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Dark background card
    path = QPainterPath()
    path.addRoundedRect(0, 0, width, height, radius, radius)
    painter.fillPath(path, QColor(35, 35, 35))
    painter.setPen(QColor(255, 255, 255, 20))
    painter.drawPath(path)

    # Draw small video icon centered
    icon_pix = FluentIcon.VIDEO.qicon().pixmap(24, 24)

    ix = (width - 24) // 2
    iy = (height - 24) // 2
    painter.setOpacity(0.4)
    painter.drawPixmap(ix, iy, icon_pix)
    painter.end()
    return target


class HistoryItemWidget(QWidget):
    def __init__(
        self, filepath: str, show_thumbnail: bool = True, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.filepath = filepath
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(14)

        self.thumb_label: QLabel | None = None
        if show_thumbnail:
            self.thumb_label = QLabel(self)
            self.thumb_label.setFixedSize(100, 56)
            self._load_or_request_thumbnail()
            layout.addWidget(self.thumb_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 2, 0, 2)
        text_layout.setSpacing(2)

        filename = os.path.basename(filepath)
        self.name_label = BodyLabel(filename, self)
        self.name_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #ffffff;")

        self.path_label = CaptionLabel(filepath, self)
        self.path_label.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.45);")

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.path_label)
        layout.addLayout(text_layout, 1)

    def _load_or_request_thumbnail(self) -> None:
        if not self.thumb_label:
            return

        if has_thumbnail(self.filepath):
            pix = QPixmap(get_thumbnail_path(self.filepath))
            if not pix.isNull():
                self.thumb_label.setPixmap(make_rounded_pixmap(pix))
                return

        # Show placeholder and request thumbnail in background
        self.thumb_label.setPixmap(create_placeholder_pixmap())
        get_thumbnail_manager().request_thumbnail(self.filepath)

    def update_thumbnail(self, thumb_path: str) -> None:
        if self.thumb_label and os.path.exists(thumb_path):
            pix = QPixmap(thumb_path)
            if not pix.isNull():
                self.thumb_label.setPixmap(make_rounded_pixmap(pix))


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

        self._item_widgets: dict[str, HistoryItemWidget] = {}

        # Connect background thumbnail manager signal
        get_thumbnail_manager().thumbnail_ready.connect(self._on_thumbnail_ready)

        self.reload_history()

    def reload_history(self) -> None:
        self.list_widget.clear()
        self._item_widgets.clear()

        config = load_config()
        show_thumb = config.show_history_thumbnails

        paths = get_history()
        for path in paths:
            item = QListWidgetItem(self.list_widget)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item_h = 68 if show_thumb else 46
            item.setSizeHint(QSize(0, item_h))

            w = HistoryItemWidget(path, show_thumbnail=show_thumb)
            self._item_widgets[os.path.normpath(path)] = w
            self.list_widget.setItemWidget(item, w)

    def _on_thumbnail_ready(self, video_path: str, thumb_path: str) -> None:
        norm = os.path.normpath(video_path)
        if norm in self._item_widgets:
            self._item_widgets[norm].update_thumbnail(thumb_path)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.file_selected.emit(path)
