import sqlite3
from datetime import datetime

from core.config import DB_PATH
from db.schema import init_db


def add_to_history(file_path: str, db_path: str = DB_PATH) -> None:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    opened_at = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO history (file_path, opened_at) VALUES (?, ?)",
        (file_path, opened_at),
    )
    conn.commit()
    conn.close()


def get_history(limit: int = 50, db_path: str = DB_PATH) -> list[str]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get unique file paths ordered by most recently opened
    cursor.execute(
        """
        SELECT file_path
        FROM history
        GROUP BY file_path
        ORDER BY MAX(opened_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows]
