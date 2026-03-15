"""
Application factory and startup lifecycle.
Startup sequence (from design doc):
  1. Load config
  2. Initialize graph (OSMnx)
  3. Create DB tables
  4. Seed vehicles
  5. Accept HTTP requests
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from adapters.db.database import engine
from adapters.db.models import Base
from adapters.geo.osmnx_graph_adapter import OsmnxGraphAdapter
from adapters.supply.simulated_supply import SimulatedSupplyAdapter
from adapters.db.database import async_session_factory
from api.dependencies import set_graph_adapter
from api.middleware import global_exception_handler
from api.routers import routing, simulation, supply


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("=" * 60)
    print("  Innopolis Multimodal Transit System — Starting Up")
    print("=" * 60)

    # Step 1: Load Innopolis graph
    graph_adapter = OsmnxGraphAdapter()
    graph_adapter.load()
    set_graph_adapter(graph_adapter)

    # Step 2: Create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] Tables created / verified.")

    # Step 3: Seed vehicles
    async with async_session_factory() as session:
        supply_adapter = SimulatedSupplyAdapter(session, graph_adapter)
        await supply_adapter.seed_vehicles()

    print("=" * 60)
    print("  READY — Accepting requests")
    print("=" * 60)

    yield

    # --- SHUTDOWN ---
    await engine.dispose()
    print("[APP] Shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Innopolis Multimodal Transit API",
        description="Thesis simulation backend.",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",       # Vite dev server
            "http://localhost:3000",        # CRA dev server
            "capacitor://localhost",        # Mobile app
            "*",                            # Allow all for thesis demos
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handler
    app.add_exception_handler(Exception, global_exception_handler)

    # Routers
    app.include_router(supply.router)
    app.include_router(routing.router)
    app.include_router(simulation.router)

    # Health check
    @app.get("/healthz")
    async def healthz():
        return {"status": "ready"}

    return app


app = create_app()
