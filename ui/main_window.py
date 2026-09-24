import os
import sys

# Ensure project root is in PATH so python-mpv can find mpv-2.dll
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["PATH"] = current_dir + os.pathsep + os.environ.get("PATH", "")
if hasattr(os, "add_dll_directory"):
    try:
        os.add_dll_directory(current_dir)
    except Exception:
        pass

if sys.platform == "win32":
    try:
        import win32api
        from PyQt6.QtGui import QCursor
        def _safe_get_cursor_pos() -> tuple[int, int]:
            pos = QCursor.pos()
            return (pos.x(), pos.y())
        win32api.GetCursorPos = _safe_get_cursor_pos
    except Exception:
        pass

from PyQt6.QtCore import QPoint, QSize, Qt, QTimer, QObject, QEvent
from PyQt6.QtGui import QKeySequence, QResizeEvent, QShortcut, QIcon, QCursor, QMouseEvent, QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, NavigationItemPosition

def get_round_icon(image_path: str) -> QIcon:
    from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
    from PyQt6.QtCore import Qt
    img = QPixmap(image_path)
    size = min(img.width(), img.height())
    img = img.copy((img.width() - size)//2, (img.height() - size)//2, size, size)
    
    out_pix = QPixmap(size, size)
    out_pix.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(out_pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, img)
    painter.end()
    
    return QIcon(out_pix)

class VideoTitleLabel(QLabel):
    """Centered, elided label for displaying current video filename in the title bar."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = ""
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet(
            "QLabel { color: rgba(255, 255, 255, 0.85); font-size: 13px; font-weight: 500; background: transparent; }"
        )

    def setText(self, text: str) -> None:
        self._full_text = text
        self.updateGeometry()
        self._update_text()

    def full_text(self) -> str:
        return self._full_text

    def sizeHint(self) -> QSize:
        if not self._full_text:
            return QSize(0, 48)
        fm = self.fontMetrics()
        w = min(650, fm.horizontalAdvance(self._full_text) + 20)
        return QSize(w, 48)

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._update_text()

    def _update_text(self) -> None:
        if not self._full_text:
            super().setText("")
            return
        fm = self.fontMetrics()
        w = max(50, self.width() - 10)
        super().setText(fm.elidedText(self._full_text, Qt.TextElideMode.ElideMiddle, w))

class WindowEdgeResizer(QObject):
    """Provides native edge and corner window resizing via Qt's startSystemResize."""
    BORDER_SIZE = 10

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self.window = window
        self._cursor_active = False

    def get_edges(self, global_pos: QPoint) -> tuple[Qt.Edge | None, Qt.CursorShape | None]:
        if not self.window.isVisible() or self.window.isFullScreen() or self.window.isMaximized():
            return None, None

        geo = self.window.geometry()
        x = global_pos.x() - geo.x()
        y = global_pos.y() - geo.y()
        w = geo.width()
        h = geo.height()
        b = self.BORDER_SIZE

        if x < 0 or x > w or y < 0 or y > h:
            return None, None

        left = (x <= b)
        right = (x >= w - b)
        top = (y <= b)
        bottom = (y >= h - b)

        # Do not block close/min/max buttons in top-right
        if top and x >= w - 140:
            top = False

        if left and top:
            return (Qt.Edge.LeftEdge | Qt.Edge.TopEdge), Qt.CursorShape.SizeFDiagCursor
        if right and bottom:
            return (Qt.Edge.RightEdge | Qt.Edge.BottomEdge), Qt.CursorShape.SizeFDiagCursor
        if right and top:
            return (Qt.Edge.RightEdge | Qt.Edge.TopEdge), Qt.CursorShape.SizeBDiagCursor
        if left and bottom:
            return (Qt.Edge.LeftEdge | Qt.Edge.BottomEdge), Qt.CursorShape.SizeBDiagCursor
        if left:
            return Qt.Edge.LeftEdge, Qt.CursorShape.SizeHorCursor
        if right:
            return Qt.Edge.RightEdge, Qt.CursorShape.SizeHorCursor
        if top:
            return Qt.Edge.TopEdge, Qt.CursorShape.SizeVerCursor
        if bottom:
            return Qt.Edge.BottomEdge, Qt.CursorShape.SizeVerCursor

        return None, None

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if not event or not self.window:
            return False

        t = event.type()
        if t in (QEvent.Type.Leave, QEvent.Type.WindowDeactivate):
            if self._cursor_active:
                QApplication.restoreOverrideCursor()
                self._cursor_active = False
            return False

        if t == QEvent.Type.MouseMove:
            pos = QCursor.pos()
            edges, cursor = self.get_edges(pos)
            if cursor:
                if not self._cursor_active:
                    QApplication.setOverrideCursor(cursor)
                    self._cursor_active = True
                else:
                    QApplication.changeOverrideCursor(cursor)
            elif self._cursor_active:
                QApplication.restoreOverrideCursor()
                self._cursor_active = False

        elif t == QEvent.Type.MouseButtonPress:
            if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                pos = QCursor.pos()
                edges, _ = self.get_edges(pos)
                if edges:
                    if self._cursor_active:
                        QApplication.restoreOverrideCursor()
                        self._cursor_active = False
                    handle = self.window.windowHandle()
                    if handle:
                        handle.startSystemResize(edges)
                        return True

        return False

from core.mixer import build_lavfi_complex
from core.player_interface import PlayerInterface
from core.types import MixSelection
from db.history import add_to_history
from ui.components.history_panel import HistoryPanel
from ui.components.player_controls import PlayerControls
from ui.components.tracks_panel import TracksPanel
from ui.player_widget import PlayerWidget




try:
    from core.player import MpvPlayer

    HAS_MPV = True
except (OSError, ImportError):
    HAS_MPV = False


class MainWindow(FluentWindow):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Frostplay")
        self.setWindowIcon(get_round_icon("img/Frostplay_logo.png"))
        
        # Configure the title bar icon (round logo placed in TitleBar at top-left next to 'Frostplay')
        self.titleBar.hBoxLayout.insertSpacing(0, 12)
        self.titleBar.iconLabel.setFixedSize(22, 22)
        self.titleBar.iconLabel.setPixmap(get_round_icon("img/Frostplay_logo.png").pixmap(22, 22))
        self.titleBar.iconLabel.show()

        # Disconnect auto-sync of window title to titleLabel so 'Frostplay' stays next to the logo
        try:
            self.windowTitleChanged.disconnect(self.titleBar.setTitle)
        except Exception:
            pass

        # Compensate spacing so title label is mathematically centered between left icon/text and right buttons
        self.titleBar.hBoxLayout.insertSpacing(3, 37)

        # Centered video title in the TitleBar
        self.video_title_label = VideoTitleLabel(self.titleBar)
        self.titleBar.hBoxLayout.insertWidget(5, self.video_title_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.titleBar.hBoxLayout.insertStretch(6, 1)

        # Set border width for frameless hit test
        self.BORDER_WIDTH = 10

        # Install native system edge and corner resizer for 100% reliable mouse resizing
        self._resizer = WindowEdgeResizer(self)
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.installEventFilter(self._resizer)

        self.resize(1000, 700)

        # Center the window
        desktop = QApplication.primaryScreen()
        if desktop:
            geom = desktop.availableGeometry()
            w, h = geom.width(), geom.height()
            self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.player: PlayerInterface | None = None
        self._mpv_initialized = False

        # Native window (mpv) cannot be animated/faded properly by Qt,
        # so we disable the interface transition animation.
        self.stackedWidget.setAnimationEnabled(False)
        self.stackedWidget.setStyleSheet(
            "QStackedWidget { border: none; border-radius: 0px; background-color: transparent; }"
        )

        self._init_navigation()
        self._init_shortcuts()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_player_state)
        self.timer.start(500)

    def _init_shortcuts(self) -> None:
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.shortcut_space.activated.connect(self._on_play_pause)

        self.shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.shortcut_left.activated.connect(self._on_seek_left)

        self.shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.shortcut_right.activated.connect(self._on_seek_right)

        self.shortcut_f = QShortcut(QKeySequence(Qt.Key.Key_F), self)
        self.shortcut_f.activated.connect(self._toggle_fullscreen)

        self.shortcut_c = QShortcut(QKeySequence(Qt.Key.Key_C), self)
        self.shortcut_c.activated.connect(self._toggle_crop)

    def _init_navigation(self) -> None:
        # --- Player page ---
        self.player_frame = QFrame()
        self.player_frame.setObjectName("Player")

        main_layout = QHBoxLayout(self.player_frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        from qfluentwidgets import SimpleCardWidget
        self.player_container = SimpleCardWidget(self.player_frame)
        self.player_container.setObjectName("PlayerContainer")

        container_layout = QVBoxLayout(self.player_container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(5)

        self.player_widget = PlayerWidget(self.player_container)
        self.player_widget.clicked.connect(self._on_play_pause)
        self.player_widget.doubleClicked.connect(self._toggle_fullscreen)
        self.player_widget.open_requested.connect(self._on_open_video)
        self.player_widget.file_dropped.connect(self._open_file)
        container_layout.addWidget(self.player_widget, stretch=1)

        self.controls = PlayerControls(self.player_container)
        self.controls.play_pause_clicked.connect(self._on_play_pause)
        self.controls.seek_requested.connect(self._on_seek)
        self.controls.open_requested.connect(self._on_open_video)
        self.controls.close_requested.connect(self._on_close_video)
        self.controls.btn_tracks.clicked.connect(self._show_tracks_menu)
        container_layout.addWidget(self.controls)

        main_layout.addWidget(self.player_container, stretch=1)

        # Tracks menu (popup)
        self.tracks_panel = TracksPanel(self)
        self.tracks_panel.mix_changed.connect(self._on_mix_changed)
        self.tracks_panel.master_volume_changed.connect(self._on_master_volume_changed)


        self.addSubInterface(
            self.player_frame,
            FIF.PLAY,
            "Player",
            position=NavigationItemPosition.TOP,
        )

        # --- History page ---
        self.history_frame = QFrame()
        self.history_frame.setObjectName("HistoryFrame")
        history_layout = QVBoxLayout(self.history_frame)
        history_layout.setContentsMargins(10, 10, 10, 10)
        history_layout.setSpacing(0)

        self.history_panel = HistoryPanel(self.history_frame)
        history_layout.addWidget(self.history_panel)

        self.history_panel.file_selected.connect(
            self._on_history_file_selected
        )
        self.addSubInterface(
            self.history_frame,
            FIF.HISTORY,
            "History",
            position=NavigationItemPosition.TOP,
        )

        self.settings_frame = QFrame()
        self.settings_frame.setObjectName("SettingsFrame")
        settings_layout = QVBoxLayout(self.settings_frame)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(0)

        from ui.components.settings_panel import SettingsPanel
        self.settings_panel = SettingsPanel(self.settings_frame)
        settings_layout.addWidget(self.settings_panel)

        self.addSubInterface(
            self.settings_frame,
            FIF.SETTING,
            "Settings",
            position=NavigationItemPosition.BOTTOM,
        )
        # Hide top menu and back buttons as requested
        self.navigationInterface.setMenuButtonVisible(False)
        self.navigationInterface.setReturnButtonVisible(False)

        # Shift navigation items down so they start below the TitleBar
        self.navigationInterface.panel.topLayout.insertSpacing(0, 48)

        # Visually center buttons: shift right to compensate for the 3px left indicator
        self.navigationInterface.panel.topLayout.setContentsMargins(7, 0, 1, 0)
        self.navigationInterface.panel.bottomLayout.setContentsMargins(7, 0, 1, 0)

        # Prevent the navigation panel from auto-expanding
        self.navigationInterface.setMinimumExpandWidth(99999)


        # Add visual separator between sidebar and content
        self.player_frame.setStyleSheet("QFrame#Player { border-left: 1px solid rgba(255, 255, 255, 0.08); }")
        self.history_frame.setStyleSheet("QFrame#HistoryFrame { border-left: 1px solid rgba(255, 255, 255, 0.08); }")
        self.settings_frame.setStyleSheet("QFrame#SettingsFrame { border-left: 1px solid rgba(255, 255, 255, 0.08); }")

    def resizeEvent(self, e: "QResizeEvent | None") -> None:
        super().resizeEvent(e)
        self.titleBar.move(0, 0)
        self.titleBar.resize(self.width(), self.titleBar.height())
        self.titleBar.raise_()
        if hasattr(self, "navigationInterface"):
            QTimer.singleShot(50, self.navigationInterface.update)
            QTimer.singleShot(50, self.update)



    # -- MPV lifecycle --------------------------------------------------

    def showEvent(self, event: "QShowEvent") -> None:  # type: ignore[name-defined]  # noqa: F821
        super().showEvent(event)
        if not self._mpv_initialized:
            self._mpv_initialized = True
            QTimer.singleShot(0, self._init_mpv)

    def _init_mpv(self) -> None:
        if HAS_MPV and self.player is None:
            self.player = MpvPlayer(
                wid=int(self.player_widget.winId())
            )

    def closeEvent(self, e: "QCloseEvent | None") -> None:
        if hasattr(self, "_resizer"):
            app_inst = QApplication.instance()
            if app_inst:
                app_inst.removeEventFilter(self._resizer)
        super().closeEvent(e)

    # -- Slots ----------------------------------------------------------

    def _open_file(self, filepath: str) -> None:
        if not self.player:
            return
        filename = os.path.basename(filepath)
        self.video_title_label.setText(filename)
        self.setWindowTitle(f"Frostplay - {filename}")
        self.player_widget.hide_placeholder()
        self.player.open(filepath)
        self.tracks_panel.set_tracks(self.player.get_tracks())
        add_to_history(filepath)
        self.history_panel.reload_history()
        
        # Hide sidebar to leave purely the video
        self.navigationInterface.hide()

    def _show_tracks_menu(self) -> None:
        if self.tracks_panel.isHidden():
            # Ensure the panel has calculated its final size before positioning
            self.tracks_panel.adjustSize()
            
            # Place in the bottom right, above the player controls
            top_right_of_controls = self.controls.mapToGlobal(QPoint(self.controls.width(), 0))
            self.tracks_panel.move(
                top_right_of_controls.x() - self.tracks_panel.width() - 10,
                top_right_of_controls.y() - self.tracks_panel.height() - 10
            )
            self.tracks_panel.show()
        else:
            self.tracks_panel.hide()

    def _on_open_video(self) -> None:
        from core.config import load_config
        config = load_config()
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            config.default_folder or "",
            "Video Files (*.mkv *.mp4 *.avi);;All Files (*)",
        )
        if filepath:
            self._open_file(filepath)

    def _on_close_video(self) -> None:
        if self.player:
            self.player.close()
        self.video_title_label.setText("")
        self.setWindowTitle("Frostplay")
        self.player_widget.show_placeholder()
        self.controls.set_duration(0.0)
        self.controls.update_position(0.0)
        self.tracks_panel.set_tracks([])
        self.tracks_panel.hide()
        
        # Show sidebar again
        self.navigationInterface.show()

    def _on_history_file_selected(self, filepath: str) -> None:
        self._open_file(filepath)
        self.stackedWidget.setCurrentWidget(self.player_frame)

    def _on_mix_changed(self, selections: list[MixSelection]) -> None:
        if not self.player:
            return
        lavfi_str = build_lavfi_complex(selections)
        self.player.set_mix(lavfi_str)

    def _on_master_volume_changed(self, volume: int) -> None:
        if self.player:
            self.player.set_volume(volume)

    def _update_player_state(self) -> None:
        if self.player:
            try:
                pos = self.player.get_position()
                dur = self.player.get_duration()
                if dur > 0:
                    self.controls.set_duration(dur)
                self.controls.update_position(pos)
                self.controls.set_playing_state(self.player.is_playing())
            except Exception:
                # Catch shutdown errors if the timer fires while mpv is closing
                pass

    def _on_play_pause(self) -> None:
        if self.player:
            self.player.play_pause()
            self.controls.set_playing_state(self.player.is_playing())

    def _on_seek(self, value: float) -> None:
        if self.player:
            self.player.seek(value)

    def _on_seek_left(self) -> None:
        if self.player:
            pos = self.player.get_position()
            self._on_seek(max(0, pos - 10))

    def _on_seek_right(self) -> None:
        if self.player:
            pos = self.player.get_position()
            self._on_seek(min(self.player.get_duration(), pos + 10))

    def _toggle_crop(self) -> None:
        if not self.player:
            return
        # Toggle panscan in mpv to fill the screen (crop) or show black bars
        current = getattr(self.player.mpv, 'panscan', 0.0)
        if current > 0.5:
            self.player.mpv.panscan = 0.0
        else:
            self.player.mpv.panscan = 1.0

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.titleBar.show()
            self.navigationInterface.show()
            self.player_frame.layout().setContentsMargins(10, 10, 10, 10)
            self.player_frame.setStyleSheet("QFrame#Player { border-left: 1px solid rgba(255, 255, 255, 0.08); }")
            self.player_container.layout().setContentsMargins(10, 10, 10, 10)
            self.player_container.setStyleSheet("")
        else:
            self.showFullScreen()
            self.titleBar.hide()
            self.navigationInterface.hide()
            self.player_frame.layout().setContentsMargins(0, 0, 0, 0)
            self.player_frame.setStyleSheet("QFrame#Player { border-left: none; }")
            self.player_container.layout().setContentsMargins(0, 0, 0, 0)
            self.player_container.setStyleSheet("SimpleCardWidget#PlayerContainer { background-color: black; border-radius: 0px; border: none; }")
