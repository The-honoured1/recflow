from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
import functools
import asyncio
from typing import Optional, Callable, List

from ..engine import AsyncEngine

def create_admin_router(engine: AsyncEngine, prefix: str = "/recflow/admin"):
    """
    Creates a FastAPI APIRouter exposing the RecFlow Admin Dashboard.
    Usage: app.include_router(create_admin_router(engine))
    """
    router = APIRouter(prefix=prefix, tags=["recflow_admin"])
    dashboard_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'dashboard.html')

    @router.get("", response_class=HTMLResponse)
    @router.get("/", response_class=HTMLResponse)
    async def index():
        # Fallback if admin html doesn't exist
        if not os.path.exists(dashboard_path):
            return "<html><body><h1>RecFlow Admin Dummy</h1></body></html>"
            
        with open(dashboard_path, "r") as f:
            return f.read()

    @router.get("/api/stats")
    async def stats():
        return JSONResponse(await engine.get_stats_async())

    @router.get("/api/rules")
    async def get_rules():
        return JSONResponse(engine.rules.to_dict())

    @router.post("/api/rules")
    async def set_rules(request: Request):
        data = await request.json()
        engine.rules.from_dict(data)
        return JSONResponse({"status": "updated"})

    return router


class RecFlowMiddleware(BaseHTTPMiddleware):
    """
    Automatically tracks views for authenticated users passing through specific route prefixes.
    Does not block the HTTP response by utilizing asyncio tasks.
    """
    def __init__(self, app, engine: AsyncEngine, target_prefixes: List[str] = None):
        super().__init__(app)
        self.engine = engine
        self.target_prefixes = target_prefixes or ["/api/items", "/api/products"]

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Only track successful GET requests as 'views' implicitly
        if request.method == "GET" and response.status_code == 200:
            path = request.url.path
            for prefix in self.target_prefixes:
                if path.startswith(prefix):
                    user_id = getattr(request.state, "user_id", None)
                    if user_id:
                        # Extract trailing item_id from URL: e.g., /api/products/123
                        item_id = path.rstrip("/").split("/")[-1]
                        # Discard if it's just the root list path
                        if item_id and item_id != prefix.strip("/").split("/")[-1]:
                            asyncio.create_task(
                                self.engine.track_interaction_async(user_id, item_id, "view")
                            )
                    break
                    
        return response

def track_interaction(event_type: str, item_id_param: str):
    """
    Decorator to automatically track fine-grained actions utilizing FastAPI BackgroundTasks.
    Requires `request: Request`, `background_tasks: BackgroundTasks`, and `engine: AsyncEngine = Depends(...)` in route signature.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            background_tasks: BackgroundTasks = kwargs.get("background_tasks")
            engine: AsyncEngine = kwargs.get("engine")
            request: Request = kwargs.get("request")
            
            item_id = kwargs.get(item_id_param)
            
            if background_tasks and engine and request and item_id:
                user_id = getattr(request.state, "user_id", "anonymous")
                background_tasks.add_task(
                    engine.track_interaction_async, user_id, str(item_id), event_type
                )
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator
