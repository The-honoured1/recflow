from fastapi import FastAPI, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
import contextlib

from recflow import AsyncEngine
from recflow.ext.fastapi import RecFlowMiddleware, track_interaction, get_engine, create_admin_router

# 1. Initialize AsyncEngine with Redis 
# (Fallback to Memory for the example if Redis isn't running locally)
try:
    import redis
    redis.Redis(host='localhost', port=6379, socket_connect_timeout=1).ping()
    STORAGE_URI = "redis://localhost:6379/0"
except Exception:
    print("Warning: Redis not found locally. Falling back to high-performance InMemoryStorage.")
    STORAGE_URI = ":memory:"

engine = AsyncEngine(storage_uri=STORAGE_URI)

# Configure some deterministic business logic rules
engine.rules.add_event_weight("view", 1.0)
engine.rules.add_event_weight("purchase", 10.0)
engine.rules.set_popularity_weight(1.5)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Expose the singleton to the application scope
    app.state.recflow_engine = engine
    
    # Preload a dummy catalog
    await engine.update_item_async("Shoes_Nike", {"category": "apparel", "type": "organic"})
    await engine.update_item_async("Shoes_Adidas", {"category": "apparel", "type": "sponsored"})
    await engine.update_item_async("Hat", {"category": "apparel"})
    yield
    # Teardown logic
    engine.clear()

app = FastAPI(lifespan=lifespan)

# 2. Add Automatic Tracking Middleware
# Any GET request starting with /api/products will automatically generate a View event 
# in the background without blocking the HTTP worker thread.
app.add_middleware(
    RecFlowMiddleware, 
    engine=engine, 
    target_prefixes=["/api/products"]
)

# 3. Mount the RecFlow Metric Dashboard safely
app.include_router(create_admin_router(engine))

# Dummy Auth Middleware to simulate a real-world JWT token user extraction
@app.middleware("http")
async def mock_auth_middleware(request: Request, call_next):
    request.state.user_id = "user_chris_99"
    return await call_next(request)


# ---------------- APPLICATION ROUTES ----------------

@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """
    Because of RecFlowMiddleware, merely rendering this endpoint 
    will securely push an async footprint to Redis.
    """
    return {"message": f"Rendering Product Page: {product_id}"}


@app.post("/api/products/{product_id}/buy")
@track_interaction(event_type="purchase", item_id_param="product_id")
async def purchase_product(
    product_id: str, 
    request: Request,
    background_tasks: BackgroundTasks,
    engine: AsyncEngine = Depends(get_engine)
):
    """
    If you need manual granular tracking logic outside simple views, 
    use the decorator to queue a FastAPI BackgroundTask implicitly.
    """
    # -> run heavy payment processing async ...
    return {"status": "success", "message": f"Purchased {product_id}"}


@app.get("/api/recommendations")
async def get_recommendations(request: Request, engine: AsyncEngine = Depends(get_engine)):
    """
    Fetch personalized rankings using the Non-Blocking Candidate/Scoring pipeline.
    """
    user_id = getattr(request.state, "user_id", "anonymous")
    recs = await engine.get_recommendations_async(user_id, limit=5)
    return {"user": user_id, "recommended_products": recs}


if __name__ == "__main__":
    import uvicorn
    print(f"--- Booting Enterprise FastAPI Server :: Storage={STORAGE_URI} ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)
