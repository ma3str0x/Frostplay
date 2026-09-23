from typing import Any

from ui.main_window import MainWindow


def test_main_window_creation(qtbot: Any) -> None:
    """Smoke test to ensure the main window can be created and doesn't crash."""
    # Note: qtbot automatically manages the application instance in pytest-qt
    window = MainWindow()
    qtbot.addWidget(window)
    assert window is not None
    assert window.windowTitle() == "Frostplay"
