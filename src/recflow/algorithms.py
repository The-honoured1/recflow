import time
import json
from typing import List
from collections import defaultdict

class PluggableAlgorithm:
    def get_recommendations(self, engine, user_id: str, limit: int) -> List[str]:
        raise NotImplementedError("Custom algorithms must implement get_recommendations")


class SQLCoOccurrenceAlgorithm(PluggableAlgorithm):
    """The default fallback algorithm utilizing SQL Jaccard intersections and Rules Engine weights."""
    
    def get_recommendations(self, engine, user_id: str, limit: int) -> List[str]:
        history_records = engine.storage.get_user_history(user_id, limit=50)
        
        if not history_records:
            return engine._get_popular_items(limit)
            
        interacted_items = set(r["item_id"] for r in history_records)
        current_time = time.time()
        
        user_item_weights = {}
        for r in history_records:
            w = engine.rules.event_weights.get(r['event_type'], 1.0)
            decay = engine._calculate_time_decay(r['timestamp'], current_time)
            user_item_weights[r['item_id']] = user_item_weights.get(r['item_id'], 0) + (w * decay)

        history_item_ids = tuple(user_item_weights.keys())
        if not history_item_ids:
            pop = engine._get_popular_items(limit + len(interacted_items))
            return [p for p in pop if p not in interacted_items][:limit]
            
        placeholders = ",".join("?" * len(history_item_ids))
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
        
        with engine.storage._get_connection() as conn:
            cursor = conn.cursor()
            params = list(history_item_ids) * 2 + [user_id]
            cursor.execute(query, params)
            candidate_interactions = cursor.fetchall()
            
        candidate_scores = defaultdict(float)
        for c_item, c_event, c_time in candidate_interactions:
            w = engine.rules.event_weights.get(c_event, 1.0)
            decay = engine._calculate_time_decay(c_time, current_time)
            candidate_scores[c_item] += w * decay
            
        if not candidate_scores:
            pop = engine._get_popular_items(limit + len(interacted_items))
            return [p for p in pop if p not in interacted_items][:limit]
            
        if engine.rules.property_boosts:
            cand_item_ids = tuple(candidate_scores.keys())
            placeholders = ",".join("?" * len(cand_item_ids))
            
            with engine.storage._get_connection() as conn:
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
                for boost in engine.rules.property_boosts:
                    if meta.get(boost["key"]) == boost["value"]:
                        candidate_scores[c_item] *= boost["multiplier"]
                        
        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        return [c for c, score in sorted_candidates][:limit]
