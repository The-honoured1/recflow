from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os

def create_admin_router(engine, prefix="/recflow/admin"):
    """
    Creates a FastAPI APIRouter exposing the RecFlow Admin Dashboard.
    Usage: app.include_router(create_admin_router(engine))
    """
    router = APIRouter(prefix=prefix, tags=["recflow_admin"])
    dashboard_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'dashboard.html')

    @router.get("", response_class=HTMLResponse)
    @router.get("/", response_class=HTMLResponse)
    async def index():
        with open(dashboard_path, "r") as f:
            return f.read()

    @router.get("/api/stats")
    async def stats():
        return JSONResponse(engine.get_stats())

    @router.get("/api/rules")
    async def get_rules():
        return JSONResponse(engine.rules.to_dict())

    @router.post("/api/rules")
    async def set_rules(request: Request):
        data = await request.json()
        engine.rules.from_dict(data)
        return JSONResponse({"status": "updated"})

    return router
