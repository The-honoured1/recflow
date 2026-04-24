import time
import json
from typing import List, Dict, Optional
from collections import defaultdict

from .storage import SQLiteStorage
from .rules import RulesEngine
from .algorithms import PluggableAlgorithm, SQLCoOccurrenceAlgorithm


class Engine:
    """
    RecFlow Backend Recommendation Engine.
    Tracks live analytics and dynamically delegates to registered Algorithms.
    """
    def __init__(self, storage_uri="recflow.db"):
        if storage_uri.startswith("sqlite:///"):
            storage_uri = storage_uri.replace("sqlite:///", "")
        
        self.storage = SQLiteStorage(db_path=storage_uri)
        self.rules = RulesEngine()
        
        # Algorithm Strategy pattern
        self.algorithms = {"sql_cooccurrence": SQLCoOccurrenceAlgorithm()}
        
    def register_algorithm(self, name: str, algorithm: PluggableAlgorithm):
        """Allows developers to inject Deep Learning / PyTorch algorithm instances dynamically."""
        self.algorithms[name] = algorithm

    def track_interaction(self, user: str, item: str, event_type: str = "view", timestamp: Optional[float] = None):
        if timestamp is None:
            timestamp = time.time()
        self.storage.record_interaction(user, item, event_type, timestamp)
        
    def update_item(self, item: str, metadata: Dict):
        self.storage.update_metadata(item, json.dumps(metadata))
        
    def _calculate_time_decay(self, interaction_time, current_time):
        days_diff = (current_time - interaction_time) / (24 * 3600)
        if days_diff < 0:
             days_diff = 0
        return 0.5 ** (days_diff / self.rules.recency_half_life_days)
        
    def get_recommendations(self, user: str, limit: int = 10) -> List[str]:
        """Delegates output generation to the Admin's selected Algorithm logic."""
        algo_name = self.rules.active_algorithm
        algo = self.algorithms.get(algo_name)
        
        if not algo:
            print(f"Warning: algorithm '{algo_name}' not found. Defaulting to sql_cooccurrence.")
            algo = self.algorithms.get("sql_cooccurrence")
            
        return algo.get_recommendations(self, user, limit)
        
    def _get_popular_items(self, limit: int) -> List[str]:
        query = """
            SELECT item_id, COUNT(*) as cnt 
            FROM interactions 
            GROUP BY item_id 
            ORDER BY cnt DESC 
            LIMIT ?
        """
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return [row[0] for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """Returns tracking stats to the dashboard."""
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COUNT(DISTINCT user_id), COUNT(DISTINCT item_id) FROM interactions")
            total_events, total_users, total_items = cursor.fetchone()
            
            cursor.execute("SELECT event_type, COUNT(*) as cnt FROM interactions GROUP BY event_type ORDER BY cnt DESC")
            events = [{"type": row[0], "count": row[1]} for row in cursor.fetchall()]
            
        return {
            "total_interactions": total_events or 0,
            "total_users": total_users or 0,
            "total_items": total_items or 0,
            "event_breakdown": events,
            "registered_algorithms": list(self.algorithms.keys())
        }

    def clear(self):
        with self.storage._get_connection() as conn:
            conn.execute("DELETE FROM interactions")
            conn.execute("DELETE FROM item_metadata")
            conn.commit()
