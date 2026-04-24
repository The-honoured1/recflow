import time
from typing import Dict, List
from .storage import BaseStorage
from .rules import RulesEngine

class ScoringEngine:
    """Computes relevance scores deteministically."""
    def __init__(self, rules: RulesEngine):
        self.rules = rules

    def _calculate_time_decay(self, interaction_time: float, current_time: float) -> float:
        days_diff = (current_time - interaction_time) / (24 * 3600)
        days_diff = max(0.0, days_diff)
        return 0.5 ** (days_diff / self.rules.recency_half_life_days)

    def score_candidates(self, user_id: str, candidate_ids: List[str], storage: BaseStorage) -> Dict[str, float]:
        """
        Calculates scores based on multiple factors.
        """
        scores = {cid: 0.0 for cid in candidate_ids}
        
        user_history = storage.get_user_history(user_id, limit=200)
        
        # Count frequency bounds
        frequency_count = {cid: 0 for cid in candidate_ids}
        for r in user_history:
            if r["item_id"] in frequency_count:
                frequency_count[r["item_id"]] += 1
                
        candidate_metadata = {cid: storage.get_item_metadata(cid) for cid in candidate_ids}
        
        # Get global popularity reference
        global_popular_items = storage.get_popular_items(limit=1000)
        popularity_rank = {item_id: idx for idx, item_id in enumerate(global_popular_items)}

        for cid in candidate_ids:
            score = 1.0 # base score
            
            # Apply Popularity Boost
            if cid in popularity_rank:
                rank = popularity_rank[cid]
                # Logarithmic/Fractional boost mapping
                boost = self.rules.popularity_boost_weight * (1.0 / (rank + 1))
                score += boost
                
            # Apply Property Boosts
            meta = candidate_metadata.get(cid, {})
            for boost in self.rules.property_boosts:
                # We specifically check dictionary value matches for dynamic injection
                if meta.get(boost["key"]) == boost["value"]:
                    score *= boost["multiplier"]
                    
            # Apply Frequency Penalty (Anti-spam)
            freq = frequency_count[cid]
            if freq > 0:
                score *= (self.rules.repetition_penalty_decay ** freq)
                
            scores[cid] = score

        return scores
