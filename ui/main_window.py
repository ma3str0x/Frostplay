import os

from PyQt6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QCloseEvent,
    QCursor,
    QIcon,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPixmap,
    QResizeEvent,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    FluentWindow,
    MenuAnimationType,
    NavigationItemPosition,
    RoundMenu,
    SimpleCardWidget,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from core.config import load_config
from core.media_properties import get_media_properties
from core.mixer import build_lavfi_complex
from core.player_interface import PlayerInterface
from core.preview_generator import PreviewGenerator
from core.types import MixSelection
from db.history import add_to_history
from ui.components.history_panel import HistoryPanel
from ui.components.player_controls import PlayerControls
from ui.components.properties_dialog import PropertiesDialog
from ui.components.timeline_preview import TimelinePreview
from ui.components.tracks_panel import TracksPanel
from ui.components.volume_indicator import VolumeIndicator
from ui.player_widget import PlayerWidget

try:
    from core.player import MpvPlayer

    HAS_MPV = True
except (OSError, ImportError):
    HAS_MPV = False


def get_round_icon(image_path: str) -> QIcon:
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
            "QLabel { color: rgba(255, 255, 255, 0.85); "
            "font-size: 13px; font-weight: 500; background: transparent; }"
        )

    def setText(self, text: str | None) -> None:
        self._full_text = text or ""
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


class AspectBridge(QObject):
    aspect_changed = pyqtSignal(float)


class MainWindow(FluentWindow):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self._aspect_bridge = AspectBridge(self)
        self._aspect_bridge.aspect_changed.connect(lambda _: self._update_blanket_fill())
        self.setWindowTitle("Frostplay")
        self.setWindowIcon(get_round_icon("img/Frostplay_logo.png"))

        # Configure the title bar icon (round logo placed at top-left)
        self.titleBar.hBoxLayout.insertSpacing(0, 12)
        self.titleBar.iconLabel.setFixedSize(22, 22)
        self.titleBar.iconLabel.setPixmap(get_round_icon("img/Frostplay_logo.png").pixmap(22, 22))
        self.titleBar.iconLabel.show()

        # Disconnect auto-sync of window title to titleLabel so 'Frostplay' stays next to the logo
        try:
            self.windowTitleChanged.disconnect(self.titleBar.setTitle)
        except Exception:
            pass

        # Compensate spacing so title label is mathematically centered
        self.titleBar.hBoxLayout.insertSpacing(3, 37)

        # Centered video title in the TitleBar
        self.video_title_label = VideoTitleLabel(self.titleBar)
        self.titleBar.hBoxLayout.insertWidget(
            5, self.video_title_label, 0, Qt.AlignmentFlag.AlignCenter
        )
        self.titleBar.hBoxLayout.insertStretch(6, 1)

        self._current_filepath: str | None = None
        self.prop_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        self.prop_shortcut.activated.connect(self._show_properties_dialog)


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

        self._blanket_fill_timer = QTimer(self)
        self._blanket_fill_timer.setSingleShot(True)
        self._blanket_fill_timer.setInterval(120)
        self._blanket_fill_timer.timeout.connect(self._update_blanket_fill)

        self.preview_generator = PreviewGenerator(self)
        self.preview_generator.frame_available.connect(self._on_preview_frame_available)
        self.timeline_preview = TimelinePreview(self)

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

        self.shortcut_b = QShortcut(QKeySequence(Qt.Key.Key_B), self)
        self.shortcut_b.activated.connect(self._toggle_blanket_fill)

    def _init_navigation(self) -> None:
        # --- Player page ---
        self.player_frame = QFrame()
        self.player_frame.setObjectName("Player")

        main_layout = QHBoxLayout(self.player_frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

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
        self.player_widget.wheel_scrolled.connect(self._on_player_wheel_scrolled)
        container_layout.addWidget(self.player_widget, stretch=1)

        self.controls = PlayerControls(self.player_container)
        self.controls.play_pause_clicked.connect(self._on_play_pause)
        self.controls.seek_requested.connect(self._on_seek)
        self.controls.open_requested.connect(self._on_open_video)
        self.controls.close_requested.connect(self._on_close_video)
        self.controls.btn_tracks.clicked.connect(self._show_tracks_menu)
        self.controls.btn_more.clicked.connect(self._show_more_menu)
        self.controls.slider_hover_moved.connect(self._on_timeline_hover_moved)
        self.controls.slider_hover_left.connect(self._on_timeline_hover_left)
        container_layout.addWidget(self.controls)

        main_layout.addWidget(self.player_container, stretch=1)

        # Tracks menu (popup)
        self.tracks_panel = TracksPanel(self)
        self.tracks_panel.mix_changed.connect(self._on_mix_changed)
        self.tracks_panel.master_volume_changed.connect(self._on_master_volume_changed)

        # Volume OSD indicator (top-right of player)
        self.volume_indicator = VolumeIndicator(self)


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

        self.settings_panel.history_preview_changed.connect(
            lambda _: self.history_panel.reload_history()
        )
        self.settings_panel.volume_boost_changed.connect(self.tracks_panel.set_allow_volume_200)
        self.settings_panel.blanket_fill_changed.connect(self._on_blanket_fill_changed)
        self.tracks_panel.set_allow_volume_200(self.settings_panel.config.allow_volume_200)

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
        b_border = "border-left: 1px solid rgba(255, 255, 255, 0.08);"
        self.player_frame.setStyleSheet(f"QFrame#Player {{ {b_border} }}")
        self.history_frame.setStyleSheet(f"QFrame#HistoryFrame {{ {b_border} }}")
        self.settings_frame.setStyleSheet(f"QFrame#SettingsFrame {{ {b_border} }}")

    def resizeEvent(self, e: "QResizeEvent | None") -> None:
        super().resizeEvent(e)
        self.titleBar.move(0, 0)
        self.titleBar.resize(self.width(), self.titleBar.height())
        self.titleBar.raise_()
        if hasattr(self, "navigationInterface"):
            QTimer.singleShot(50, self.navigationInterface.update)
            QTimer.singleShot(50, self.update)
        if hasattr(self, "volume_indicator") and self.volume_indicator.isVisible():
            vol = self.tracks_panel.master_vol_slider.value()
            self.volume_indicator.show_volume(vol, self.player_widget)
        if hasattr(self, "_blanket_fill_timer"):
            self._blanket_fill_timer.start()



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
            self.player.set_aspect_ratio_callback(
                self._aspect_bridge.aspect_changed.emit
            )
            from core.config import load_config
            cfg = load_config()
            self.player.set_blanket_fill(
                self.player_widget.width(),
                self.player_widget.height(),
                cfg.blanket_fill,
            )

    def changeEvent(self, event: QEvent | None) -> None:
        if event is not None and event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                if hasattr(self, "volume_indicator"):
                    self.volume_indicator.hide()
                if hasattr(self, "tracks_panel"):
                    self.tracks_panel.hide()
        super().changeEvent(event)

    def closeEvent(self, e: "QCloseEvent | None") -> None:
        if hasattr(self, "_resizer"):
            app_inst = QApplication.instance()
            if app_inst:
                app_inst.removeEventFilter(self._resizer)
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
        if hasattr(self, "volume_indicator"):
            self.volume_indicator.close()
        if hasattr(self, "tracks_panel"):
            self.tracks_panel.close()
        if hasattr(self, "timeline_preview"):
            self.timeline_preview.close()
        if hasattr(self, "preview_generator"):
            self.preview_generator.close()
        if self.player:
            try:
                self.player.destroy()
            except Exception:
                pass
            self.player = None
        super().closeEvent(e)


    # -- Slots ----------------------------------------------------------

    def _open_file(self, filepath: str) -> None:
        if not self.player:
            return
        self._current_filepath = filepath
        filename = os.path.basename(filepath)
        self.video_title_label.setText(filename)
        self.setWindowTitle(f"Frostplay - {filename}")
        self.player_widget.hide_placeholder()
        self.player.open(filepath)
        self.preview_generator.load_video(filepath)
        self.tracks_panel.set_tracks(self.player.get_tracks())
        add_to_history(filepath)
        self.history_panel.reload_history()
        QTimer.singleShot(1000, lambda: self._capture_active_thumbnail(filepath))
        QTimer.singleShot(50, self._update_blanket_fill)

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

    def _show_more_menu(self) -> None:
        menu = RoundMenu(parent=self)

        # Properties action
        prop_action = Action(FIF.INFO, "Properties", self)
        prop_action.setShortcut("Ctrl+I")
        prop_action.triggered.connect(lambda: QTimer.singleShot(50, self._show_properties_dialog))
        menu.addAction(prop_action)

        menu.addSeparator()

        # Speed submenu
        speed_menu = RoundMenu("Speed", parent=menu)
        speed_menu.setIcon(FIF.SPEED_HIGH)
        current_speed = self.player.get_speed() if self.player else 1.0

        speeds = [
            (0.25, "0.25x"),
            (0.5, "0.5x"),
            (1.0, "1.0x (Normal)"),
            (1.25, "1.25x"),
            (1.5, "1.5x"),
            (2.0, "2.0x"),
        ]


        for s_val, s_label in speeds:
            act = Action(s_label, self)
            act.setCheckable(True)
            if abs(current_speed - s_val) < 0.05:
                act.setChecked(True)
            act.triggered.connect(lambda checked, s=s_val: self._set_speed(s))
            speed_menu.addAction(act)

        menu.addMenu(speed_menu)

        # Blanket fill toggle action
        cfg = load_config()
        blanket_act = Action(FIF.ZOOM, "Blanket Fill", self)
        blanket_act.setCheckable(True)
        blanket_act.setChecked(cfg.blanket_fill)
        blanket_act.triggered.connect(self._toggle_blanket_fill)
        menu.addAction(blanket_act)

        # Pop up smoothly above btn_more
        pos = self.controls.btn_more.mapToGlobal(QPoint(0, 0))
        menu.exec(pos, aniType=MenuAnimationType.PULL_UP)

    def _set_speed(self, speed: float) -> None:
        if self.player:
            self.player.set_speed(speed)

    def _show_properties_dialog(self) -> None:
        if not self._current_filepath:
            return
        props = get_media_properties(self._current_filepath, self.player)
        dlg = PropertiesDialog(props, self)
        dlg.exec()

    def _on_open_video(self) -> None:
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
        self._current_filepath = None
        if self.player:
            self.player.close()
        self.video_title_label.setText("")
        self.setWindowTitle("Frostplay")
        self.player_widget.show_placeholder()
        self.controls.set_duration(0.0)
        self.controls.update_position(0.0)
        self.tracks_panel.set_tracks([])
        self.tracks_panel.hide()
        if hasattr(self, "timeline_preview"):
            self.timeline_preview.hide()
        if hasattr(self, "preview_generator"):
            self.preview_generator.close()

        # Show sidebar again
        self.navigationInterface.show()

    def _on_timeline_hover_moved(self, seconds: float, x_in_slider: int) -> None:
        if self._current_filepath and self.controls.slider.isEnabled():
            pix = self.preview_generator.get_preview(seconds)
            self.timeline_preview.set_preview(seconds, pix)
            self.timeline_preview.position_above(self.controls.slider, x_in_slider)

    def _on_timeline_hover_left(self) -> None:
        if hasattr(self, "timeline_preview"):
            self.timeline_preview.hide()

    def _on_preview_frame_available(self, sec: int, pixmap: QPixmap) -> None:
        if hasattr(self, "timeline_preview") and self.timeline_preview.isVisible():
            self.timeline_preview.update_pixmap_if_matching(sec, pixmap)

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

    def _on_player_wheel_scrolled(self, delta: int) -> None:
        config = load_config()
        if not config.wheel_volume_control:
            return

        current_vol = self.tracks_panel.master_vol_slider.value()
        step = 5 if delta > 0 else -5
        max_vol = 200 if config.allow_volume_200 else 100
        new_vol = max(0, min(max_vol, current_vol + step))
        self.tracks_panel.master_vol_slider.setValue(new_vol)
        self.volume_indicator.show_volume(new_vol, self.player_widget)

    def _capture_active_thumbnail(self, filepath: str) -> None:
        from core.thumbnail import get_thumbnail_path
        thumb_path = get_thumbnail_path(filepath)
        if not os.path.exists(thumb_path) and self.player and self.player.is_playing():
            try:
                mpv_obj = getattr(self.player, "mpv", None)
                if mpv_obj is not None:
                    mpv_obj.command("screenshot-to-file", thumb_path, "video")
                    self.history_panel.reload_history()
            except Exception:
                pass

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
        mpv_obj = getattr(self.player, "mpv", None)
        if mpv_obj is not None:
            current = float(getattr(mpv_obj, "panscan", 0.0) or 0.0)
            setattr(mpv_obj, "panscan", 0.0 if current > 0.5 else 1.0)

    def _toggle_fullscreen(self) -> None:
        pf_layout = self.player_frame.layout()
        pc_layout = self.player_container.layout()
        if self.isFullScreen():
            self.showNormal()
            self.titleBar.show()
            self.navigationInterface.show()
            if pf_layout is not None:
                pf_layout.setContentsMargins(10, 10, 10, 10)
            self.player_frame.setStyleSheet(
                "QFrame#Player { border-left: 1px solid rgba(255, 255, 255, 0.08); }"
            )
            if pc_layout is not None:
                pc_layout.setContentsMargins(10, 10, 10, 10)
            self.player_container.setStyleSheet("")
        else:
            self.showFullScreen()
            self.titleBar.hide()
            self.navigationInterface.hide()
            if pf_layout is not None:
                pf_layout.setContentsMargins(0, 0, 0, 0)
            self.player_frame.setStyleSheet("QFrame#Player { border-left: none; }")
            if pc_layout is not None:
                pc_layout.setContentsMargins(0, 0, 0, 0)
            self.player_container.setStyleSheet(
                "SimpleCardWidget#PlayerContainer { "
                "background-color: black; border-radius: 0px; border: none; }"
            )
        QTimer.singleShot(50, self._update_blanket_fill)

    def _update_blanket_fill(self) -> None:
        if self.player:
            from core.config import load_config
            cfg = load_config()
            self.player.set_blanket_fill(
                self.player_widget.width(),
                self.player_widget.height(),
                cfg.blanket_fill,
            )

    def _on_blanket_fill_changed(self, enabled: bool) -> None:
        if self.player:
            self.player.set_blanket_fill(
                self.player_widget.width(),
                self.player_widget.height(),
                enabled,
            )

    def _toggle_blanket_fill(self) -> None:
        from core.config import save_config
        cfg = load_config()
        new_val = not cfg.blanket_fill
        cfg.blanket_fill = new_val
        save_config(cfg)
        if hasattr(self, "settings_panel"):
            self.settings_panel.blanket_fill_checkbox.setChecked(new_val)
        self._on_blanket_fill_changed(new_val)
