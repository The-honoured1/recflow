import random
from typing import List
from .storage import BaseStorage
from .scoring import ScoringEngine
from .candidates import CandidatePoolManager

class Ranker:
    """Orchestrates candidate generation, scoring, and output ranking."""
    def __init__(self, pool_manager: CandidatePoolManager, scoring_engine: ScoringEngine, exploration_ratio: float = 0.1):
        self.pool_manager = pool_manager
        self.scoring_engine = scoring_engine
        self.exploration_ratio = exploration_ratio

    def get_ranked_items(self, user_id: str, storage: BaseStorage, limit: int = 10) -> List[str]:
        # 1. Candidate Generation
        candidates = self.pool_manager.generate_all(user_id, storage, limit_per_generator=50)
        candidate_ids = list(candidates)

        if not candidate_ids:
            # Fallback to popular items if no candidates found
            return storage.get_popular_items(limit=limit)

        # 2. Scoring
        scores = self.scoring_engine.score_candidates(user_id, candidate_ids, storage)

        # 3. Sort by score
        sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ranked_ids = [cid for cid, score in sorted_candidates]

        # 4. Filter out items user already interacted heavily with?
        # Done implicitly by repetition penalty in ScoringEngine

        # 5. Application of Exploration Injection
        final_list = ranked_ids[:limit]
        
        # Inject items randomly if configured
        if self.exploration_ratio > 0 and final_list:
            num_exploration = max(1, int(limit * self.exploration_ratio))
            trending = storage.get_popular_items(limit=100)
            trending_not_in_cand = [t for t in trending if t not in candidate_ids]
            
            if trending_not_in_cand:
                samples = random.sample(trending_not_in_cand, min(num_exploration, len(trending_not_in_cand)))
                for item in samples:
                    idx = random.randint(0, len(final_list) - 1) if final_list else 0
                    if idx < len(final_list):
                        final_list[idx] = item
                    else:
                        final_list.append(item)

        return final_list[:limit]
