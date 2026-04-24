from flask import Blueprint, jsonify, request, g
import os
import functools
import threading

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
        if not os.path.exists(dashboard_path):
            return "<html><body><h1>RecFlow Admin Dummy</h1></body></html>"
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


def setup_flask_tracking(app, engine, target_prefixes=None):
    """
    Hooks into Flask's after_request to automatically track interactions
    asynchronously using Daemon Threads to prevent blocking HTTP workers.
    """
    if target_prefixes is None:
        target_prefixes = ["/api/items", "/api/products"]

    @app.after_request
    def recflow_auto_track(response):
        if request.method == "GET" and response.status_code == 200:
            path = request.path
            for prefix in target_prefixes:
                if path.startswith(prefix):
                    user_id = None
                    if 'user_id' in getattr(request, 'session', {}):
                        user_id = request.session['user_id']
                    elif hasattr(g, 'user') and g.user:
                        user_id = getattr(g.user, 'id', getattr(g.user, 'username', str(g.user)))
                        
                    if user_id:
                        item_id = path.rstrip("/").split("/")[-1]
                        if item_id and item_id != prefix.strip("/").split("/")[-1]:
                            def background_track(uid, iid):
                                engine.track_interaction(str(uid), str(iid), "view")
                            
                            thread = threading.Thread(target=background_track, args=(user_id, item_id))
                            thread.daemon = True
                            thread.start()
                    break
        return response


def track_interaction(engine, event_type: str, item_kwarg: str):
    """
    Flask route decorator for manual interaction tracking (purchases, clicks).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            item_id = kwargs.get(item_kwarg)
            user_id = None
            if 'user_id' in getattr(request, 'session', {}):
                user_id = request.session['user_id']
            elif hasattr(g, 'user') and g.user:
                user_id = getattr(g.user, 'id', getattr(g.user, 'username', str(g.user)))
                
            if item_id and user_id:
                def run_background():
                    engine.track_interaction(str(user_id), str(item_id), event_type)
                t = threading.Thread(target=run_background)
                t.daemon = True
                t.start()
                
            return func(*args, **kwargs)
        return wrapper
    return decorator
