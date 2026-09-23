import os
import sys

# Ensure the current directory is in PATH so python-mpv can find mpv-2.dll
current_dir = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = current_dir + os.pathsep + os.environ.get("PATH", "")
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(current_dir)

from PyQt6.QtGui import QColor  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
from qfluentwidgets import Theme, setTheme, setThemeColor  # noqa: E402

from db.schema import init_db  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


def main() -> None:
    # Initialize DB (if not exists)
    init_db()

    app = QApplication(sys.argv)
    setTheme(Theme.DARK)
    setThemeColor(QColor("#00a3a6"))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
