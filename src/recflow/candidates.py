import abc
from typing import List, Set
from .storage import BaseStorage

class CandidateGenerator(abc.ABC):
    @abc.abstractmethod
    def generate(self, user_id: str, storage: BaseStorage, limit: int = 100) -> List[str]:
        """Returns a list of candidate item_ids."""
        pass

class RecentInteractionsGenerator(CandidateGenerator):
    def generate(self, user_id: str, storage: BaseStorage, limit: int = 100) -> List[str]:
        history = storage.get_user_history(user_id, limit=limit)
        # Dictionary comprehension preserves insertion order while removing duplicates (Python 3.7+)
        return list(dict.fromkeys(record["item_id"] for record in history))

class TrendingGenerator(CandidateGenerator):
    def generate(self, user_id: str, storage: BaseStorage, limit: int = 100) -> List[str]:
        return storage.get_popular_items(limit=limit)

class SimilarItemsGenerator(CandidateGenerator):
    """
    Finds items that other users interacted with, given they interacted 
    with the same items as the target user. (Item-based collaborative filtering).
    """
    def generate(self, user_id: str, storage: BaseStorage, limit: int = 100) -> List[str]:
        history = storage.get_user_history(user_id, limit=50)
        if not history:
            return []
            
        interacted_items = set(r["item_id"] for r in history)
        candidates = []
        
        # Simple collaborative filtering finding co-occurring items
        for item_id in interacted_items:
            item_interactions = storage.get_item_interactions(item_id, limit=20)
            for interaction in item_interactions:
                other_user = interaction.get("user_id")
                if other_user and other_user != user_id:
                    other_history = storage.get_user_history(other_user, limit=20)
                    for r in other_history:
                        if r["item_id"] not in interacted_items:
                            candidates.append(r["item_id"])
                            if len(set(candidates)) >= limit:
                                return list(dict.fromkeys(candidates))[:limit]
        
        return list(dict.fromkeys(candidates))[:limit]

class CandidatePoolManager:
    """Manages retrieving candidates from multiple algorithms."""
    def __init__(self):
        self.generators: List[CandidateGenerator] = [
            RecentInteractionsGenerator(),
            SimilarItemsGenerator(),
            TrendingGenerator()
        ]
        
    def generate_all(self, user_id: str, storage: BaseStorage, limit_per_generator: int = 100) -> Set[str]:
        all_candidates = set()
        for gen in self.generators:
            candidates = gen.generate(user_id, storage, limit=limit_per_generator)
            all_candidates.update(candidates)
        return all_candidates
