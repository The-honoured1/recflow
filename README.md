# RecFlow

A production-grade, stateful backend recommendation engine library tailored for high-scale, event-driven environments. 

**RecFlow** takes a different approach: instead of requiring clunky Machine Learning pipelines (TensorFlow/PyTorch) and massive offline models, RecFlow is an autonomous engine designed natively for your core backend. It consumes user interactions in real-time, builds fast memory footprints, dynamically computes deterministic relevance heuristics, and serves highly tailored rankings from route handlers instantly.

---

## 🔥 Enterprise Features

- **Distributed Redis Scaling**: Seamlessly synchronize user footprints across multiple server nodes using the `RedisStorage` adapter.
- **Asynchronous Execution (`AsyncEngine`)**: Native support for Python's `asyncio`. Offload heavy ranking and IO operations to background threads to keep your API response times sub-10ms.
- **Framework Auto-Tracking**: Drop-in Middlewares for **FastAPI**, **Django**, and **Flask** that automatically record "view" events without manual instrumentation.
- **Deterministic Pipeline & Rule Configurations**: Calculate final rankings through pure business logic. Easily tweak mathematical multipliers for Popularity bias, Item Property matching (e.g. `type: sponsored`), and Time Recency Decay.
- **Modular Candidate Generators**: Pluggable strategies to gather candidates (Trending, Recent, Social/Collaborative Graph).
- **Anti-Spam Metrics**: Reduces score impacts of items that users frequently see but never convert on, ensuring content freshness.

---

## 🏗️ System Architecture

RecFlow is engineered sequentially to provide deep modularity:

1. **Event Ingestion**: Hook `engine.track_interaction()` or use framework-specific middlewares.
2. **State Management**: Sub-millisecond tracking via `InMemoryStorage`, `SQLiteStorage`, or `RedisStorage`.
3. **Candidate Orchestration**: Multi-strategy generator system picking top pools of relationships concurrently.
4. **Scoring Engine**: Evaluates Jaccard-like decay weights, frequency penalties, and dynamic metadata bonuses.
5. **Ranking Pipeline**: Dedupes, sorts conditionally, handles exploration injection, and limits output.

---

## 📦 Installation

```bash
# Core only (SQLite/InMemory)
pip install recflow

# With Redis support
pip install recflow[redis]

# With FastAPI/Django/Flask integrations
pip install recflow[fastapi]
pip install recflow[django]
pip install recflow[flask]
```

---

## 🚀 Framework Integration

### FastAPI (Async Performance)
```python
from fastapi import FastAPI, Depends
from recflow import AsyncEngine
from recflow.ext.fastapi import RecFlowMiddleware, get_engine

app = FastAPI()
engine = AsyncEngine(storage_uri="redis://localhost:6379/0")

# Auto-track product views in the background
app.add_middleware(RecFlowMiddleware, engine=engine, target_prefixes=["/api/products"])

@app.get("/api/recommendations")
async def recommendations(request: Request, engine: AsyncEngine = Depends(get_engine)):
    user_id = request.state.user_id
    # Non-blocking recommendation fetch
    return await engine.get_recommendations_async(user_id, limit=10)
```

### Django (Enterprise Middleware)
```python
# settings.py
MIDDLEWARE = [
    ...,
    'recflow.ext.django.RecFlowMiddleware',
]
RECFLOW_STORAGE_URI = "redis://cache-server:6379/1"
RECFLOW_TARGET_PREFIXES = ["/store/items/"]
```

---

## ⚙️ Advanced Metrics & Rules

```python
# Configure recency decay (30-day half-life)
engine.rules.set_recency_decay(half_life_days=30.0)

# Anti-Spam: Drop score by 20% for every past interaction
engine.rules.set_repetition_penalty(decay_factor=0.8)

# Artificial boost for sponsored content
engine.rules.add_metadata_boost("is_sponsored", True, multiplier=3.5)
```

