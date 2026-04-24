from flask import Blueprint, jsonify, request
import os

def create_admin_blueprint(engine, url_prefix="/recflow/admin"):
    """
    Creates a Flask Blueprint exposing the RecFlow Admin Dashboard.
    Usage: app.register_blueprint(create_admin_blueprint(engine))
    """
    bp = Blueprint('recflow_admin', __name__, url_prefix=url_prefix)
    
    dashboard_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'dashboard.html')

    @bp.route("/")
    @bp.route("")
    def index():
        with open(dashboard_path, "r") as f:
            return f.read()
            
    @bp.route("/api/stats")
    def stats():
        return jsonify(engine.get_stats())
        
    @bp.route("/api/rules", methods=["GET", "POST"])
    def rules():
        if request.method == "POST":
            engine.rules.from_dict(request.json)
            return jsonify({"status": "updated"})
        return jsonify(engine.rules.to_dict())
        
    return bp
