# RecFlow (Engine)

A high-performance, stateful recommendation backend engine for your application. **RecFlow** manages its own tracking persistence and intelligently clusters implicit connections in real-time, giving you programmatic control over what users see.

## Installation
```bash
pip install recflow
```

## Quick Start

Initialize the engine (defaults to an embedded SQLite database `recflow.db`) and inject your business logic:

```python
from recflow import Engine

# Instantiates a live service manager tracking in memory or disk.
engine = Engine(storage_uri="sqlite:///recflow.db")

# Programmer's Will: Add algorithmic overrides and event weights dynamically
engine.rules.add_event_weight("purchase", 5.0)
engine.rules.add_event_weight("view", 1.0)
engine.rules.add_metadata_boost("type", "sponsored", 2.0)
engine.rules.set_recency_decay(days=30)
```

Inside your application backend, just fire-and-forget events to the engine when users trigger actions:

```python
# In your application endpoints
@app.route('/view')
def on_user_view(user_id, item_id):
    engine.track_interaction(user_id, item_id, event_type="view")
```

Fetch deeply personalized suggestions live:
```python
# The engine parses the SQL interaction graph, weights recent clicks, and outputs the result in ms.
recs = engine.get_recommendations(user="user_123", limit=10)
```
