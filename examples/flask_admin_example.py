from flask import Flask
from recflow import Engine
from recflow.ext.flask import create_admin_blueprint

app = Flask(__name__)

# Initialize the backend engine
engine = Engine(storage_uri="sqlite:///:memory:")

# Populate some mock tracking data
engine.track_interaction("alice", "laptop", event_type="view")
engine.track_interaction("alice", "laptop", event_type="purchase")
engine.track_interaction("alice", "mouse", event_type="purchase")
engine.track_interaction("bob", "mouse", event_type="view")

engine.update_item("laptop", {"type": "electronics"})

# Admin Dashboard
# It will be accessible at http://127.0.0.1:5000/recflow/admin
admin_bp = create_admin_blueprint(engine)
app.register_blueprint(admin_bp)

@app.route("/")
def home():
    return "API running! Go to <a href='/recflow/admin'>/recflow/admin</a> to view the dashboard."

if __name__ == "__main__":
    print("Starting Flask Server...")
    print("Visit: http://127.0.0.1:5000/recflow/admin")
    app.run(debug=True, port=5000)
