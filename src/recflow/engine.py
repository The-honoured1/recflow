import time
import json
from typing import List, Dict, Optional

import asyncio
from .storage import BaseStorage, SQLiteStorage, InMemoryStorage, RedisStorage
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
        elif storage_uri.startswith("redis://"):
             self.storage = RedisStorage(redis_url=storage_uri)
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


class AsyncEngine(Engine):
    """
    Asynchronous adapter for RecFlow.
    Offloads synchronous storage IO and ranking algorithms to Python threadpools
    to prevent blocking async event loops like FastAPI/Uvicorn.
    """
    async def track_interaction_async(self, user: str, item: str, event_type: str = "view", timestamp: Optional[float] = None):
        await asyncio.to_thread(self.track_interaction, user, item, event_type, timestamp)
        
    async def update_item_async(self, item: str, metadata: Dict):
        await asyncio.to_thread(self.update_item, item, metadata)
        
    async def get_recommendations_async(self, user: str, limit: int = 10) -> List[str]:
        return await asyncio.to_thread(self.get_recommendations, user, limit)

    async def get_stats_async(self) -> Dict:
        return await asyncio.to_thread(self.get_stats)

