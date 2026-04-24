import sqlite3
import json
from typing import Dict, Any, List

class SQLiteStorage:
    def __init__(self, db_path="recflow.db"):
        self.db_path = db_path
        if self.db_path == ":memory:":
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=5.0)
        self._init_db()

    def _get_connection(self):
        return self._conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS item_metadata (
                    item_id TEXT PRIMARY KEY,
                    metadata_json TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON interactions(user_id, timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_item ON interactions(item_id)")
            conn.commit()

    def record_interaction(self, user_id: str, item_id: str, event_type: str, timestamp: float):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO interactions (user_id, item_id, event_type, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, item_id, event_type, timestamp)
            )
            conn.commit()
            
    def update_metadata(self, item_id: str, metadata_json: str):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO item_metadata (item_id, metadata_json) VALUES (?, ?) ON CONFLICT(item_id) DO UPDATE SET metadata_json=excluded.metadata_json",
                (item_id, metadata_json)
            )
            conn.commit()
            
    def get_user_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT item_id, event_type, timestamp FROM interactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            return [{"item_id": row[0], "event_type": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
