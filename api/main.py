"""
RoutePulse API Gateway (FastAPI)
Modular gateway implementing all Section 10 REST endpoints and accelerated SSE live stream.
"""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    health, network, plans, live, eta,
    demand, alerts, recommendations, whatif,
    scenarios, eval as eval_router, ingest, student
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Synchronise openapi.json on startup
    try:
        spec_path = Path(__file__).resolve().parent / "openapi.json"
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(app.openapi(), f, indent=2)
    except Exception:
        pass
    yield

app = FastAPI(
    title="RoutePulse API",
    version="0.1.0",
    description="Campus Transport Optimization API — Sense, Estimate, Detect, Decide, Verify, Explain.",
    lifespan=lifespan
)

# Section 10: CORS enabled for frontend web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all Section 10 API Routers under /api
app.include_router(health.router, prefix="/api")
app.include_router(network.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(live.router, prefix="/api")
app.include_router(eta.router, prefix="/api")
app.include_router(demand.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(whatif.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(eval_router.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(student.router, prefix="/api")

@app.get("/healthz")
@app.get("/health")
def root_health():
    return {"status": "ok", "service": "routepulse"}

from fastapi.staticfiles import StaticFiles

# Serve built frontend if available
web_dist_dir = Path(__file__).resolve().parent.parent / "web" / "dist"
if web_dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dist_dir), html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
