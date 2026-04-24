import time
import json
from typing import List, Dict, Optional

from .storage import BaseStorage, SQLiteStorage, InMemoryStorage
from .rules import RulesEngine
from .candidates import CandidatePoolManager
from .scoring import ScoringEngine
from .ranking import Ranker

class Engine:
    """
    RecFlow Backend Recommendation Engine.
    Engineered for high performance deterministic relevance scoring.
    """
    def __init__(self, storage_uri="recflow.db", storage_mode="auto"):
        if storage_uri == ":memory:" or storage_uri == "sqlite:///:memory:" or storage_mode == "memory":
             self.storage = InMemoryStorage()
        else:
             if storage_uri.startswith("sqlite:///"):
                 storage_uri = storage_uri.replace("sqlite:///", "")
             self.storage = SQLiteStorage(db_path=storage_uri)
             
        self.rules = RulesEngine()
        self.candidates_mgr = CandidatePoolManager()
        self.scoring = ScoringEngine(self.rules)
        self.ranker = Ranker(self.candidates_mgr, self.scoring)
        
    def track_interaction(self, user: str, item: str, event_type: str = "view", timestamp: Optional[float] = None):
        if timestamp is None:
            timestamp = time.time()
        self.storage.record_interaction(user, item, event_type, timestamp)
        
    def update_item(self, item: str, metadata: Dict):
        self.storage.update_metadata(item, json.dumps(metadata))
        
    def get_recommendations(self, user: str, limit: int = 10) -> List[str]:
        """Provides dynamic recommendations by running through the Candidate/Scoring pipeline."""
        return self.ranker.get_ranked_items(user, self.storage, limit=limit)

    def get_stats(self) -> Dict:
        """Returns tracking stats."""
        # Generic fallback since we changed BaseStorage
        return {
            "status": "Engine operational",
            "rules": self.rules.to_dict()
        }

    def clear(self):
        self.storage.clear()
