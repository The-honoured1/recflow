import pytest
import sqlite3
from recflow import Engine

@pytest.fixture
def memory_engine():
    e = Engine("sqlite:///:memory:")
    yield e
    e.clear()

def test_engine_records_and_clusters(memory_engine):
    memory_engine.rules.add_event_weight("purchase", 5.0)
    
    # User 1 buys A, B, C
    memory_engine.track_interaction("u1", "A", "purchase")
    memory_engine.track_interaction("u1", "B", "purchase")
    memory_engine.track_interaction("u1", "C", "purchase")
    
    # User 2 buys A
    memory_engine.track_interaction("u2", "A", "purchase")
    
    recs = memory_engine.get_recommendations("u2", limit=2)
    
    assert "B" in recs
    assert "C" in recs
    assert "A" not in recs
    
def test_engine_boost_rules(memory_engine):
    memory_engine.rules.add_event_weight("view", 1.0)
    memory_engine.rules.add_metadata_boost("category", "sponsored", 10.0)
    
    memory_engine.update_item("B", {"category": "sponsored"})
    
    # u1 views A, B, C
    memory_engine.track_interaction("u1", "A", "view")
    memory_engine.track_interaction("u1", "B", "view")
    memory_engine.track_interaction("u1", "C", "view")
    
    memory_engine.track_interaction("u2", "A", "view")
    
    recs = memory_engine.get_recommendations("u2", limit=2)
    assert recs[0] == "B"
