from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QKeySequence, QResizeEvent, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, NavigationItemPosition

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

    def _init_navigation(self) -> None:
        # --- Player page ---
        self.player_frame = QFrame()
        self.player_frame.setObjectName("Player")

        main_layout = QHBoxLayout(self.player_frame)
        # 10px margins all around so the card floats symmetrically
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # Left: video + controls (stretch to fill) wrapped in a Card for 2-tone look
        from qfluentwidgets import SimpleCardWidget
        left = SimpleCardWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(0)

        self.player_widget = PlayerWidget(left)
        self.player_widget.clicked.connect(self._on_play_pause)
        left_layout.addWidget(self.player_widget, stretch=1)

        self.controls = PlayerControls(left)
        self.controls.play_pause_clicked.connect(self._on_play_pause)
        self.controls.seek_requested.connect(self._on_seek)
        self.controls.open_requested.connect(self._on_open_video)
        self.controls.btn_tracks.clicked.connect(self._show_tracks_menu)
        left_layout.addWidget(self.controls)

        main_layout.addWidget(left, stretch=1)

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

        from qfluentwidgets import SimpleCardWidget
        settings_card = SimpleCardWidget(self.settings_frame)
        settings_layout.addWidget(settings_card)

        self.addSubInterface(
            self.settings_frame,
            FIF.SETTING,
            "Settings",
            position=NavigationItemPosition.BOTTOM,
        )
        # Hide top menu and back buttons as requested
        self.navigationInterface.setMenuButtonVisible(False)
        self.navigationInterface.setReturnButtonVisible(False)

        # Prevent the navigation panel from auto-expanding in fullscreen mode
        self.navigationInterface.setMinimumExpandWidth(99999)

        # Shift items down by 1 position (approx 44px) to compensate
        self.navigationInterface.panel.topLayout.insertSpacing(0, 44)

    def resizeEvent(self, e: "QResizeEvent | None") -> None:
        super().resizeEvent(e)
        # Force navigation panel and main window to repaint after resize
        # This fixes visual glitches when maximizing/going fullscreen with embedded libmpv
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

    # -- Slots ----------------------------------------------------------

    def _open_file(self, filepath: str) -> None:
        if not self.player:
            return
        self.player_widget.hide_placeholder()
        self.player.open(filepath)
        self.tracks_panel.set_tracks(self.player.get_tracks())
        add_to_history(filepath)
        self.history_panel.reload_history()

    def _show_tracks_menu(self) -> None:
        if self.tracks_panel.isHidden():
            # Calculate position to show above the btn_tracks
            pos = self.controls.btn_tracks.mapToGlobal(QPoint(0, 0))
            self.tracks_panel.move(
                pos.x() + self.controls.btn_tracks.width() - self.tracks_panel.width(),
                pos.y() - self.tracks_panel.height() - 10
            )
            self.tracks_panel.show()
        else:
            self.tracks_panel.hide()

    def _on_open_video(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Video Files (*.mkv *.mp4 *.avi);;All Files (*)",
        )
        if filepath:
            self._open_file(filepath)

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
