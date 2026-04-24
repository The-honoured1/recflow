import time
from recflow import Engine

print("Initializing RecFlow Backend Engine...")
# We use an in-memory database for the quickstart, but you can use "recflow.db" to persist to disk
engine = Engine(storage_uri="sqlite:///:memory:")

print("Developer configures programmatic weights and business logic...")
engine.rules.add_event_weight("view", 1.0)
engine.rules.add_event_weight("add_to_cart", 3.0)
engine.rules.add_event_weight("purchase", 10.0)

# Boost items marked as 'sponsored' dynamically
engine.rules.add_metadata_boost("type", "sponsored", multiplier=2.5)

print("\nSimulating Application Live Events...")
engine.update_item("IPhone_Case", {"type": "sponsored"})
engine.update_item("IPhone", {"type": "organic"})
engine.update_item("Charger", {"type": "organic"})

# User A tracks heavily via application routes
engine.track_interaction("userA", "IPhone", "view")
engine.track_interaction("userA", "IPhone", "purchase")
engine.track_interaction("userA", "IPhone_Case", "purchase")
engine.track_interaction("userA", "Charger", "purchase")

# User B comes in and just views an iPhone
engine.track_interaction("userB", "IPhone", "view")

print("\n--- Requesting Live Recommendations for User B ---")
recs = engine.get_recommendations("userB", limit=2)
print(f"Recommendations: {recs}")
# It instantly clusters user B with user A's footprint, finding the case and charger. 
# It boosts the Case because of the 'sponsored' developer rule!
