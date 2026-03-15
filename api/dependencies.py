"""
FastAPI dependency injection wiring.
Connects abstract ports to concrete adapters.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.db.database import get_session
from adapters.db.persistence_adapter import PostgresPersistenceAdapter
from adapters.supply.simulated_supply import SimulatedSupplyAdapter
from core.ports.graph_port import GraphPort
from core.ports.persistence_port import PersistencePort
from core.ports.vehicle_supply_port import VehicleSupplyPort
from core.services.routing_service import RoutingService
from core.services.scenario_service import ScenarioService
from core.services.supply_service import SupplyService

# The graph adapter is a module-level singleton, set during startup
_graph_adapter: GraphPort | None = None


def set_graph_adapter(adapter: GraphPort) -> None:
    global _graph_adapter
    _graph_adapter = adapter


def get_graph_port() -> GraphPort:
    if _graph_adapter is None:
        raise RuntimeError("Graph adapter not initialized.")
    return _graph_adapter


def get_persistence(
    session: AsyncSession = Depends(get_session),
) -> PersistencePort:
    return PostgresPersistenceAdapter(session)


def get_supply(
    session: AsyncSession = Depends(get_session),
    graph: GraphPort = Depends(get_graph_port),
) -> VehicleSupplyPort:
    return SimulatedSupplyAdapter(session, graph)


def get_scenario_service(
    persistence: PersistencePort = Depends(get_persistence),
) -> ScenarioService:
    return ScenarioService(persistence)


def get_supply_service(
    supply: VehicleSupplyPort = Depends(get_supply),
) -> SupplyService:
    return SupplyService(supply)


def get_routing_service(
    graph: GraphPort = Depends(get_graph_port),
    supply: VehicleSupplyPort = Depends(get_supply),
    persistence: PersistencePort = Depends(get_persistence),
    scenario: ScenarioService = Depends(get_scenario_service),
) -> RoutingService:
    return RoutingService(graph, supply, persistence, scenario)
