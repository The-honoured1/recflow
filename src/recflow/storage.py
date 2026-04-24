import sqlite3
import json
import abc
from typing import Dict, Any, List
from collections import defaultdict

class BaseStorage(abc.ABC):
    @abc.abstractmethod
    def record_interaction(self, user_id: str, item_id: str, event_type: str, timestamp: float):
        pass
        
    @abc.abstractmethod
    def update_metadata(self, item_id: str, metadata_json: str):
        pass
        
    @abc.abstractmethod
    def get_user_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        pass
        
    @abc.abstractmethod
    def get_item_metadata(self, item_id: str) -> Dict[str, Any]:
        pass
        
    @abc.abstractmethod
    def get_popular_items(self, limit: int = 100) -> List[str]:
        pass

    @abc.abstractmethod
    def get_item_interactions(self, item_id: str, limit: int = 100) -> List[Dict]:
        pass

    @abc.abstractmethod
    def clear(self):
        pass


class InMemoryStorage(BaseStorage):
    def __init__(self):
        self._user_history = defaultdict(list)
        self._item_metadata = {}
        self._item_interactions = defaultdict(list)
        self._global_popularity = defaultdict(int)

    def record_interaction(self, user_id: str, item_id: str, event_type: str, timestamp: float):
        interaction = {"item_id": item_id, "user_id": user_id, "event_type": event_type, "timestamp": timestamp}
        self._user_history[user_id].append(interaction)
        self._item_interactions[item_id].append(interaction)
        self._global_popularity[item_id] += 1

    def update_metadata(self, item_id: str, metadata_json: str):
        self._item_metadata[item_id] = json.loads(metadata_json)
        if item_id not in self._global_popularity:
            self._global_popularity[item_id] = 0

    def get_user_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        history = sorted(self._user_history.get(user_id, []), key=lambda x: x["timestamp"], reverse=True)
        return history[:limit]

    def get_item_metadata(self, item_id: str) -> Dict[str, Any]:
        return self._item_metadata.get(item_id, {})

    def get_popular_items(self, limit: int = 100) -> List[str]:
        sorted_items = sorted(self._global_popularity.items(), key=lambda x: x[1], reverse=True)
        return [item for item, count in sorted_items][:limit]
        
    def get_item_interactions(self, item_id: str, limit: int = 100) -> List[Dict]:
        interactions = sorted(self._item_interactions.get(item_id, []), key=lambda x: x["timestamp"], reverse=True)
        return interactions[:limit]

    def clear(self):
        self._user_history.clear()
        self._item_metadata.clear()
        self._item_interactions.clear()
        self._global_popularity.clear()


class SQLiteStorage(BaseStorage):
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

    def get_item_metadata(self, item_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata_json FROM item_metadata WHERE item_id = ?", (item_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return {}

    def get_popular_items(self, limit: int = 100) -> List[str]:
        query = """
            SELECT item_id, COUNT(*) as cnt 
            FROM interactions 
            GROUP BY item_id 
            ORDER BY cnt DESC 
            LIMIT ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return [row[0] for row in cursor.fetchall()]

    def get_item_interactions(self, item_id: str, limit: int = 100) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, event_type, timestamp FROM interactions WHERE item_id = ? ORDER BY timestamp DESC LIMIT ?",
                (item_id, limit)
            )
            return [{"user_id": row[0], "event_type": row[1], "timestamp": row[2]} for row in cursor.fetchall()]

    def clear(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM interactions")
            conn.execute("DELETE FROM item_metadata")
            conn.commit()


try:
    import redis
except ImportError:
    redis = None

class RedisStorage(BaseStorage):
    """
    Distributed robust storage using Redis lists and sorted sets.
    Capable of scaling synchronously array distribution.
    """
    def __init__(self, redis_url="redis://localhost:6379/0", prefix="recflow"):
        if redis is None:
            raise ImportError("Must install redis to use RedisStorage (pip install redis or recflow[redis])")
        self.r = redis.from_url(redis_url, decode_responses=True)
        self.pfx = prefix

    def _user_hist_key(self, uid): return f"{self.pfx}:u:hist:{uid}"
    def _item_meta_key(self, iid): return f"{self.pfx}:i:meta:{iid}"
    def _item_int_key(self, iid): return f"{self.pfx}:i:int:{iid}"
    def _pop_key(self): return f"{self.pfx}:global:pop"

    def record_interaction(self, user_id: str, item_id: str, event_type: str, timestamp: float):
        payload = json.dumps({
            "item_id": item_id, 
            "user_id": user_id, 
            "event_type": event_type, 
            "timestamp": timestamp
        })
        with self.r.pipeline() as pipe:
            pipe.lpush(self._user_hist_key(user_id), payload)
            pipe.ltrim(self._user_hist_key(user_id), 0, 999) # keep list size bounded
            pipe.lpush(self._item_int_key(item_id), payload)
            pipe.ltrim(self._item_int_key(item_id), 0, 999)
            pipe.zincrby(self._pop_key(), 1, item_id)
            pipe.execute()

    def update_metadata(self, item_id: str, metadata_json: str):
        self.r.set(self._item_meta_key(item_id), metadata_json)
        # initialize popularity implicitly if completely new
        self.r.zadd(self._pop_key(), {item_id: 0}, nx=True)

    def get_user_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        items = self.r.lrange(self._user_hist_key(user_id), 0, limit - 1)
        return [json.loads(i) for i in items]

    def get_item_metadata(self, item_id: str) -> Dict[str, Any]:
        data = self.r.get(self._item_meta_key(item_id))
        if data:
            try:
                return json.loads(data)
            except:
                pass
        return {}

    def get_popular_items(self, limit: int = 100) -> List[str]:
        return self.r.zrevrange(self._pop_key(), 0, limit - 1)

    def get_item_interactions(self, item_id: str, limit: int = 100) -> List[Dict]:
        items = self.r.lrange(self._item_int_key(item_id), 0, limit - 1)
        return [json.loads(i) for i in items]

    def clear(self):
        # Warning: operations like keys() can be slow on very large clusters,
        # but useful for tests/resets.
        keys = self.r.keys(f"{self.pfx}:*")
        if keys:
            self.r.delete(*keys)

