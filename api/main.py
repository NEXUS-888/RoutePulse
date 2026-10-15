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

# Serve built frontend if available; otherwise serve helpful fallback
web_dist_dir = Path(__file__).resolve().parent.parent / "web" / "dist"
if web_dist_dir.exists() and (web_dist_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(web_dist_dir), html=True), name="web")
else:
    from fastapi.responses import HTMLResponse
    @app.get("/", response_class=HTMLResponse)
    def web_fallback():
        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RoutePulse - Service Active</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0B1020; color: #F9FAFB; padding: 48px; line-height: 1.6; }
    .card { max-width: 680px; margin: 0 auto; background: #111827; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
    h1 { margin-top: 0; color: #3B82F6; font-size: 1.6rem; }
    code { background: #162032; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #F59E0B; }
    a { color: #3B82F6; text-decoration: none; font-weight: 600; }
    a:hover { text-decoration: underline; }
    .btn { display: inline-block; background: #3B82F6; color: white; padding: 10px 18px; border-radius: 6px; font-weight: bold; margin-top: 16px; margin-right: 10px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>RoutePulse Transit Optimization Engine</h1>
    <p><strong>FastAPI Backend is running successfully!</strong></p>
    <p>The pre-compiled frontend distribution in <code>web/dist</code> was not found on this machine.</p>
    <p>To access the full interactive operator dashboard:</p>
    <ol>
      <li>Run <code>npm run build</code> in the <code>web</code> directory.</li>
      <li>Or download the latest release package with pre-bundled <code>web/dist</code>.</li>
    </ol>
    <div style="margin-top: 24px;">
      <a class="btn" href="/docs">Open Swagger API Docs</a>
      <a class="btn" style="background: #10B981;" href="/healthz">System Health</a>
    </div>
  </div>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
