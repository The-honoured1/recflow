import functools
import logging

try:
    from django.conf import settings
    # Initialize global singleton for Django based on settings
    # Expects RECFLOW_STORAGE_URI to be set, defaults to Redis
    _storage_uri = getattr(settings, 'RECFLOW_STORAGE_URI', 'redis://localhost:6379/0')
    DJANGO_AVAILABLE = True
except ImportError:
    # If not using Django proper
    DJANGO_AVAILABLE = False
    _storage_uri = "redis://localhost:6379/0"

from ..engine import Engine

# In Django, standard synchronous engine works perfectly with Redis Storage
# as the IO mapping is extremely fast 
global_engine = Engine(storage_uri=_storage_uri)

class RecFlowMiddleware:
    """
    Django middleware to automatically track viewing behaviors securely.
    Add 'recflow.ext.django.RecFlowMiddleware' to your MIDDLEWARE setting.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        if DJANGO_AVAILABLE:
            self.target_prefixes = getattr(settings, 'RECFLOW_TARGET_PREFIXES', ['/products/', '/items/'])
        else:
            self.target_prefixes = ['/products/', '/items/']

    def __call__(self, request):
        response = self.get_response(request)
        
        # Fire analytics logic conditionally on successful render
        if request.method == "GET" and response.status_code == 200:
            path = request.path
            for prefix in self.target_prefixes:
                if path.startswith(prefix):
                    user_id = None
                    if hasattr(request, "user") and request.user.is_authenticated:
                        user_id = str(getattr(request.user, "username", getattr(request.user, "id", None)))
                        
                    if user_id:
                        item_id = path.rstrip("/").split("/")[-1]
                        if item_id and item_id != prefix.strip("/").split("/")[-1]:
                            # In serious production, this should be offloaded to a Celery @shared_task
                            global_engine.track_interaction(user_id, item_id, "view")
                    break

        return response


def track_interaction(event_type: str, item_kwarg: str):
    """
    Django View Decorator to manually track interactions (clicks, purchases).
    Usage: @track_interaction("purchase", item_kwarg="product_id") on the view.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            item_id = kwargs.get(item_kwarg)
            if item_id and hasattr(request, "user") and request.user.is_authenticated:
                user_id = str(getattr(request.user, "username", request.user.id))
                try:
                    global_engine.track_interaction(user_id, str(item_id), event_type)
                except Exception as e:
                    logging.error(f"RecFlow Tracking Error: {e}")
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
