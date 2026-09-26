from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap

from core.preview_generator import PreviewGenerator
from ui.components.player_controls import ClickableSlider
from ui.components.timeline_preview import TimelinePreview


def test_timeline_preview_format_time(qtbot: Any) -> None:
    preview = TimelinePreview()
    qtbot.addWidget(preview)
    assert preview._format_time(0.0) == "00:00"
    assert preview._format_time(45.0) == "00:45"
    assert preview._format_time(75.0) == "01:15"
    assert preview._format_time(3665.0) == "01:01:05"


def test_timeline_preview_set_data(qtbot: Any) -> None:
    preview = TimelinePreview()
    qtbot.addWidget(preview)

    pix = QPixmap(100, 100)
    pix.fill(QColor("red"))

    preview.set_preview(15.0, pix)
    assert preview.current_seconds == 15.0
    assert preview.time_label.text() == "00:15"
    assert preview.thumb_label.pixmap() is not None

    # Test loading placeholder when pixmap is None
    preview.set_preview(25.0, None)
    assert preview.current_seconds == 25.0
    assert preview.time_label.text() == "00:25"


def test_timeline_preview_update_matching(qtbot: Any) -> None:
    preview = TimelinePreview()
    qtbot.addWidget(preview)
    preview.current_seconds = 30.0

    pix = QPixmap(50, 50)
    pix.fill(QColor("blue"))

    # Matching second within 1.5s
    preview.update_pixmap_if_matching(30, pix)
    assert preview.thumb_label.pixmap() is not None


def test_preview_generator_caching(qtbot: Any) -> None:
    gen = PreviewGenerator()

    pix = QPixmap(20, 20)
    gen._cache[10] = pix

    # Fetch exact cached frame
    res = gen.get_preview(10.0)
    assert res is not None

    # Near frame fallback within 3 seconds
    near_res = gen.get_preview(11.0)
    assert near_res == pix

    gen.close()
    assert len(gen._cache) == 0


def test_clickable_slider_mouse_tracking(qtbot: Any) -> None:
    slider = ClickableSlider(Qt.Orientation.Horizontal)
    qtbot.addWidget(slider)
    assert slider.hasMouseTracking() is True


def test_clickable_slider_hover_does_not_seek(qtbot: Any) -> None:
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QMouseEvent

    slider = ClickableSlider(Qt.Orientation.Horizontal)
    qtbot.addWidget(slider)
    slider.setRange(0, 100)
    slider.setValue(10)
    slider.resize(200, 30)

    # Hover without mouse buttons pressed
    hover_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(150.0, 15.0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(slider.hover_moved):
        slider.mouseMoveEvent(hover_event)

    # Value should remain untouched at 10 (no seek on hover)
    assert slider.value() == 10


