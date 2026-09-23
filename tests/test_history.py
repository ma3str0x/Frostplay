from pathlib import Path

from db.history import add_to_history, get_history
from db.schema import init_db


def test_add_and_get_history(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    # Initially empty
    assert len(get_history(db_path=db_path)) == 0

    # Add items
    add_to_history("C:/movies/video1.mkv", db_path)
    add_to_history("C:/movies/video2.mp4", db_path)

    history = get_history(db_path=db_path)
    assert len(history) == 2
    assert history[0] == "C:/movies/video2.mp4" # Most recent first
    assert history[1] == "C:/movies/video1.mkv"

    # Add video1 again to test grouping and ordering
    add_to_history("C:/movies/video1.mkv", db_path)

    history_updated = get_history(db_path=db_path)
    assert len(history_updated) == 2 # Grouped, unique items
    assert history_updated[0] == "C:/movies/video1.mkv" # video1 is now most recent
    assert history_updated[1] == "C:/movies/video2.mp4"
