# RecFlow

A production-grade, stateful backend recommendation engine library tailored for high-scale, event-driven environments. 

**RecFlow** takes a different approach: instead of requiring clunky Machine Learning pipelines (TensorFlow/PyTorch) and massive offline models, RecFlow is an autonomous engine designed natively for your core backend. It consumes user interactions in real-time, builds fast memory footprints, dynamically computes deterministic relevance heuristics, and serves highly tailored rankings from route handlers instantly.

Designed out of the box for E-commerce upsells, Social Media feeds, Content platforms, and scaling web infrastructure.

---

## 🔥 Key Features

- **Blazing Fast In-Memory Stateful Engine**: Stores behavior nodes cleanly without constant read-blockings, ensuring `get_recommendations()` takes less than a millisecond.
- **Pluggable Event-Driven Storage**: Use the default `InMemoryStorage` for volatile speed or connect persistent scaling adapters (`SQLiteStorage` included, easy Redis abstraction).
- **Extensible Candidate Generators**: Provides out-of-the-box components to harvest candidate item pools:
  - `RecentInteractionsGenerator`: Re-engage users with items they recently viewed.
  - `SimilarItemsGenerator`: Harvests collaborative footprint logic by mapping connected behaviors.
  - `TrendingGenerator`: Captures global top impressions, gracefully catching "Cold Start" user cases instantly.
- **Deterministic Pipeline & Rule Configurations**: Calculate final rankings through pure business logic. Easily tweak mathematical multipliers for Popularity bias, Item Property matching (e.g. `type: sponsored`), and Time Recency Decay.
- **Anti-Spam Metrics**: Reduces score impacts of items that users frequently see but never convert on, ensuring content freshness.

---

## 🏗️ Architecture

RecFlow is engineered sequentially to give you granularity at every computational phase:

1. **Event Ingestion**: Hook `engine.track_interaction()` into your API backend to store user actions effortlessly.
2. **State Management**: Sub-millisecond tracking via unified `BaseStorage` interfaces.
3. **Candidate Orchestration**: Multi-strategy generator system picking top pools of relationships concurrently.
4. **Scoring Engine**: Evaluates Jaccard-like decay weights, frequency penalties, and dynamic metadata bonuses.
5. **Ranking Pipeline**: Dedupes, sorts conditionally, handles exploration injection, and limits output before returning final identifiers to your frontend client.

---

## 📦 Installation

RecFlow requires no external ML binaries.

```bash
pip install recflow
```

---

## 🚀 Quickstart Example

RecFlow requires no training data or batch processing. Initialize it, stream your application events sequentially, and instantly pull intelligent results.

```python
from recflow import Engine

# 1. Initialize a purely in-memory backend
engine = Engine(storage_mode="memory")

# 2. Configure Dynamic Business Logic Weights
engine.rules.add_event_weight("view", 1.0)
engine.rules.add_event_weight("add_to_cart", 3.0)
engine.rules.add_event_weight("purchase", 10.0)

# Apply a 2.5x score multiplier for any catalog item carrying 'sponsored' metadata
engine.rules.add_metadata_boost("type", "sponsored", multiplier=2.5)

# 3. Simulate Global Event Ingestion
engine.update_item("IPhone_Case", {"type": "sponsored"})
engine.update_item("IPhone", {"type": "organic"})
engine.update_item("Charger", {"type": "organic"})

# User A acts heavily
engine.track_interaction("userA", "IPhone", "view")
engine.track_interaction("userA", "IPhone", "purchase")
engine.track_interaction("userA", "IPhone_Case", "purchase")
engine.track_interaction("userA", "Charger", "purchase")

# User B is brand new (Cold Start logic), just clicks one item
engine.track_interaction("userB", "IPhone", "view")

# 4. Request Real-Time Recommendations
recs = engine.get_recommendations("userB", limit=2)
print("Recommendations for User B:", recs)
# Output: ['IPhone_Case', 'IPhone']
```

In the example above, RecFlow detects User B shares an interaction footprint with User A. It gathers all of User A's un-viewed items (the Case and Charger), scores them deterministically against User B's state, artificially boosts the Case utilizing the 'sponsored' developer rule, and delivers an instant array mapping back to the client.

---

## ⚙️ Advanced Configuration (Rules Engine)

You have total developer control over the mathematical parameters dictating user outputs:

```python
# Decay points older than 30 days by 50%
engine.rules.set_recency_decay(half_life_days=30.0)

# Penalize items a user has interacted with multiple times (Anti-Spam)
# Lowers score by 20% for every duplicate historical interaction 
engine.rules.set_repetition_penalty(decay_factor=0.8)

# Augment Popularity Bias (1.0 = Default, 2.0+ = Highly biased toward Trending)
engine.rules.set_popularity_weight(weight=2.0)
```
