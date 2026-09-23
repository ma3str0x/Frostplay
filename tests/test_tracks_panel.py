from typing import Any

from core.types import Track
from ui.components.track_row import TrackRow
from ui.components.tracks_panel import TracksPanel


def test_track_row_signals_and_selection(qtbot: Any) -> None:
    track = Track(index=1, language="eng", codec="aac")
    row = TrackRow(track)
    qtbot.addWidget(row)

    # Initial state
    sel = row.get_selection()
    assert sel.index == 1
    assert sel.volume == 1.0
    assert sel.enabled is True

    # Change slider and test signal
    with qtbot.waitSignal(row.state_changed):
        row.slider.setValue(50)

    assert row.get_selection().volume == 0.5

    # Toggle checkbox and test signal
    with qtbot.waitSignal(row.state_changed):
        # We simulate a click by toggling
        row.checkbox.setChecked(False)

    assert row.get_selection().enabled is False


def test_tracks_panel_population_and_signals(qtbot: Any) -> None:
    panel = TracksPanel()
    qtbot.addWidget(panel)

    tracks = [
        Track(index=1, language="eng", codec="aac"),
        Track(index=2, language="ukr", codec="ac3"),
    ]

    with qtbot.waitSignal(panel.mix_changed) as blocker:
        panel.set_tracks(tracks)

    selections = blocker.args[0]
    assert len(selections) == 2
    assert selections[0].index == 1
    assert selections[1].index == 2

    # Verify rows were actually created
    assert len(panel._rows) == 2

    # Change a row and ensure panel emits mix_changed
    with qtbot.waitSignal(panel.mix_changed) as blocker:
        panel._rows[0].slider.setValue(50)

    selections = blocker.args[0]
    assert selections[0].volume == 0.5
