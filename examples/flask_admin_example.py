from flask import Flask
from recflow import Engine
from recflow.algorithms import PluggableAlgorithm
from recflow.ext.flask import create_admin_blueprint

# 1. Developer builds a custom Algorithm class wrapping a deep learning pipeline
class DummyPyTorchNet(PluggableAlgorithm):
    def __init__(self):
        # Here a developer would: self.model = torch.load("model.pt")
        print("[System] Initializing PyTorch Matrix Factorization Model to GPU...")
        
    def get_recommendations(self, engine, user_id, limit):
        # We can dynamically grab the SQLite interaction footprint to pass into the Neural Net Tensor!
        print(f"[PyTorch] Passing {user_id}'s footprint into Neural layers...")
        return ["DeepLearn_Item_A", "DeepLearn_Item_B"]

app = Flask(__name__)

engine = Engine(storage_uri="sqlite:///:memory:")

# 2. Register the heavy custom algorithm seamlessly. 
engine.register_algorithm("pytorch_net_v2", DummyPyTorchNet())

# Start monitoring data
engine.track_interaction("alice", "laptop", event_type="view")
engine.track_interaction("bob", "mouse", event_type="purchase")

# 3. Mount Admin Dashboard (will show BOTH the fallback SQL and the new PyTorch Net)
admin_bp = create_admin_blueprint(engine)
app.register_blueprint(admin_bp)

@app.route("/")
def home():
    engine.get_recommendations("alice", limit=2) # This traces which algo is active
    return "API running! Go to <a href='/recflow/admin'>/recflow/admin</a> to toggle between SQL and the PyTorch Net based logic live on the server."

if __name__ == "__main__":
    app.run(debug=True, port=5000)
