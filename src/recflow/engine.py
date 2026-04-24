import time
import json
from typing import List, Dict, Optional
from collections import defaultdict

from .storage import SQLiteStorage
from .rules import RulesEngine


class Engine:
    """
    RecFlow Backend Recommendation Engine.
    Tracks live analytics and dynamically computes intersections.
    """
    def __init__(self, storage_uri="recflow.db"):
        if storage_uri.startswith("sqlite:///"):
            storage_uri = storage_uri.replace("sqlite:///", "")
        
        self.storage = SQLiteStorage(db_path=storage_uri)
        self.rules = RulesEngine()
        
    def track_interaction(self, user: str, item: str, event_type: str = "view", timestamp: Optional[float] = None):
        """Fire and forget route tracking."""
        if timestamp is None:
            timestamp = time.time()
        self.storage.record_interaction(user, item, event_type, timestamp)
        
    def update_item(self, item: str, metadata: Dict):
        """Attach properties to items so `RulesEngine` can apply logic."""
        self.storage.update_metadata(item, json.dumps(metadata))
        
    def _calculate_time_decay(self, interaction_time, current_time):
        days_diff = (current_time - interaction_time) / (24 * 3600)
        if days_diff < 0:
             days_diff = 0
        return 0.5 ** (days_diff / self.rules.recency_half_life_days)
        
    def get_recommendations(self, user: str, limit: int = 10) -> List[str]:
        """Dynamically fetch the most intelligent real-time recommendations."""
        history_records = self.storage.get_user_history(user, limit=50)
        
        if not history_records:
            return self._get_popular_items(limit)
            
        interacted_items = set(r["item_id"] for r in history_records)
        current_time = time.time()
        
        user_item_weights = {}
        for r in history_records:
            w = self.rules.event_weights.get(r['event_type'], 1.0)
            decay = self._calculate_time_decay(r['timestamp'], current_time)
            user_item_weights[r['item_id']] = user_item_weights.get(r['item_id'], 0) + (w * decay)

        history_item_ids = tuple(user_item_weights.keys())
        if not history_item_ids:
            pop = self._get_popular_items(limit + len(interacted_items))
            return [p for p in pop if p not in interacted_items][:limit]
            
        placeholders = ",".join("?" * len(history_item_ids))
        
        # Collaborative query: users who interacted with the same items
        query = f"""
            SELECT i2.item_id, i2.event_type, i2.timestamp 
            FROM interactions i1
            JOIN interactions i2 ON i1.user_id = i2.user_id
            WHERE i1.item_id IN ({placeholders})
              AND i2.item_id NOT IN ({placeholders})
              AND i1.user_id != ?
            ORDER BY i2.timestamp DESC
            LIMIT 1000
        """
        
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            params = list(history_item_ids) * 2 + [user]
            cursor.execute(query, params)
            candidate_interactions = cursor.fetchall()
            
        candidate_scores = defaultdict(float)
        for c_item, c_event, c_time in candidate_interactions:
            w = self.rules.event_weights.get(c_event, 1.0)
            decay = self._calculate_time_decay(c_time, current_time)
            candidate_scores[c_item] += w * decay
            
        if not candidate_scores:
            pop = self._get_popular_items(limit + len(interacted_items))
            return [p for p in pop if p not in interacted_items][:limit]
            
        if self.rules.property_boosts:
            cand_item_ids = tuple(candidate_scores.keys())
            placeholders = ",".join("?" * len(cand_item_ids))
            
            with self.storage._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT item_id, metadata_json FROM item_metadata WHERE item_id IN ({placeholders})", cand_item_ids)
                meta_rows = cursor.fetchall()
                
            metadata_map = {}
            for row in meta_rows:
                try:
                    metadata_map[row[0]] = json.loads(row[1])
                except:
                    pass
                    
            for c_item in candidate_scores:
                meta = metadata_map.get(c_item, {})
                for boost in self.rules.property_boosts:
                    if meta.get(boost["key"]) == boost["value"]:
                        candidate_scores[c_item] *= boost["multiplier"]
                        
        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        return [c for c, score in sorted_candidates][:limit]
        
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
        """Returns tracking stats for the Admin dashboard."""
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
            "event_breakdown": events
        }

    def clear(self):
        """Drops data, useful for testing."""
        with self.storage._get_connection() as conn:
            conn.execute("DELETE FROM interactions")
            conn.execute("DELETE FROM item_metadata")
            conn.commit()
