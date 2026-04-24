# RecFlow (Engine)

A high-performance, real-time stateful recommendation engine toolkit for backends. Rather than manually wrangling static arrays, RecFlow tracks behavioral events organically over SQLite/Redis and gives you **total architectural freedom to hot-swap advanced PyTorch/Deep Learning algorithms on the fly.**

## Core Advantages

1. **Pluggable Algorithm Strategy**: RecFlow ships with a robust SQL-based Co-Occurrence engine entirely for data collection fallback, but strictly exposes the `PluggableAlgorithm` interface. You can inject massive PyTorch `.pt` inference loops as native engine strategies without breaking your core application logic.
2. **Dashboard Controls**: Provides a fully-styled Admin Dashboard (mounts natively to FastAPI and Flask) that tracks global metric analytics dynamically.
3. **Hot-Swapping**: The administrator can instantly replace the active prediction pipeline from `sql_cooccurrence` to your custom `matrix_factorization_v2` logic straight from the backend configuration UI, all without redeploying.

## Quick Start (PyTorch Integration)

```python
from recflow import Engine
from recflow.algorithms import PluggableAlgorithm

class DeepTensorModel(PluggableAlgorithm):
    def __init__(self):
        # Load the massive external PyTorch model state
        self.model = load_my_pytorch_model()
        
    def get_recommendations(self, engine, user_id, limit):
        # 1. Ask RecFlow for the tracked interactions footprints to feed the tensor
        history = engine.storage.get_user_history(user_id)
        # 2. Run your specific deep learning inference
        return self.model.predict(history)

# Boot the engine in your application
engine = Engine(storage_uri="sqlite:///recflow.db")

# Expose the custom architecture
engine.register_algorithm("hybrid_torch_net", DeepTensorModel())
```
The Administrator can simply click the new "hybrid_torch_net" from their frontend `/admin` dashboard component, and their webserver immediately switches over all background inferences gracefully.
