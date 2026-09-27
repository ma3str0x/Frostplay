import os
import sys

# Ensure sys.stdout and sys.stderr are valid streams in frozen GUI app
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from core.perf import log_perf

# Ensure current directory and bundle directory are in PATH so python-mpv can find mpv-2.dll
if getattr(sys, "frozen", False):
    current_dir = os.path.dirname(sys.executable)
    bundle_dir = getattr(sys, "_MEIPASS", current_dir)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    bundle_dir = current_dir

for d in (current_dir, bundle_dir):
    if d and os.path.isdir(d):
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(d)
            except Exception:
                pass

# Set AppUserModelID so Windows taskbar shows Frostplay icon instead of Python's
if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("frostplay.player.1")

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

from PyQt6.QtGui import QColor  # noqa: E402
from PyQt6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
from qfluentwidgets import Theme, setTheme, setThemeColor  # noqa: E402

from db.schema import init_db  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402

IPC_SERVER_NAME = "frostplay_single_instance_ipc"


def main() -> None:
    log_perf("MAIN", "main() started")
    init_db()
    log_perf("MAIN", "db initialized")

    app = QApplication(sys.argv)
    log_perf("MAIN", "QApplication created")

    # Resolve file argument from CLI if passed
    file_to_open: str | None = None
    if len(sys.argv) > 1 and sys.argv[1]:
        cand = os.path.abspath(sys.argv[1])
        if os.path.isfile(cand):
            file_to_open = cand

    # Check if another instance of Frostplay is already running
    client_socket = QLocalSocket()
    client_socket.connectToServer(IPC_SERVER_NAME)
    if client_socket.waitForConnected(50):

        # Another instance is already running; forward file argument if present
        if file_to_open:
            client_socket.write(file_to_open.encode("utf-8"))
            client_socket.waitForBytesWritten(1000)
        client_socket.disconnectFromServer()
        sys.exit(0)

    # This is the primary instance: start IPC server
    ipc_server = QLocalServer()
    ipc_server.removeServer(IPC_SERVER_NAME)
    ipc_server.listen(IPC_SERVER_NAME)

    setTheme(Theme.DARK)
    setThemeColor(QColor("#00a3a6"))

    log_perf("MAIN", "Creating MainWindow")
    window = MainWindow(initial_file=file_to_open)
    log_perf("MAIN", "MainWindow created, showing window")
    window.show()
    log_perf("MAIN", "MainWindow show() called")

    def _on_new_connection() -> None:
        log_perf("IPC", "New IPC connection received")
        sock = ipc_server.nextPendingConnection()
        if not sock:
            return

        def _on_ready_read() -> None:
            raw = sock.readAll().data().decode("utf-8").strip()
            log_perf("IPC", f"IPC data received: {raw}")
            if raw and os.path.isfile(raw):
                window.open_file(raw)
                window.show()
                if window.isMinimized():
                    window.showNormal()
                window.raise_()
                window.activateWindow()

        sock.readyRead.connect(_on_ready_read)

    ipc_server.newConnection.connect(_on_new_connection)

    exit_code = app.exec()
    ipc_server.close()
    os._exit(exit_code)


if __name__ == "__main__":
    main()

