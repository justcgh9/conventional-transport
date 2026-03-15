"""
Main orchestrator for route calculation.
Coordinates all ports and the optimizer.
"""

from __future__ import annotations

from core.optimizer.data_generator import EdgeParameterGenerator
from core.optimizer.engine import OptimizerEngine
from core.optimizer.route_assembler import RouteAssembler
from core.ports.graph_port import GraphPort
from core.ports.persistence_port import PersistencePort
from core.ports.vehicle_supply_port import VehicleSupplyPort
from core.services.scenario_service import ScenarioService
from domain.route import Route
from domain.value_objects import GeoPoint, UserWeights
import config


class RoutingService:

    def __init__(
        self,
        graph_port: GraphPort,
        supply_port: VehicleSupplyPort,
        persistence_port: PersistencePort,
        scenario_service: ScenarioService,
    ):
        self._graph = graph_port
        self._supply = supply_port
        self._persistence = persistence_port
        self._scenario = scenario_service
        self._optimizer = OptimizerEngine()
        self._assembler = RouteAssembler(graph_port)
        self._data_gen = EdgeParameterGenerator(rng_seed=42)

    async def calculate_route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        weights: UserWeights,
    ) -> Route:

        # 1. Get active scenario
        scenario_type, physics = await self._scenario.get_active()

        # 2. Map GPS to graph nodes
        origin_node = self._graph.get_nearest_node(origin.lat, origin.lon)
        dest_node = self._graph.get_nearest_node(
            destination.lat, destination.lon
        )

        # 3. Get the full simplified graph
        graph = self._graph.get_graph()

        # 4. Get available vehicles
        scooters = await self._supply.get_available_scooters()
        drivers = await self._supply.get_available_drivers(
            origin_node, dest_node
        )

        # 5. Generate edge parameters (stochastic, per paper §3.2)
        edge_params = self._data_gen.generate(
            graph, physics, scooters, drivers
        )

        # 6. Run the MILP optimizer (paper Eq. 1-5)
        normalized_weights = weights.normalized()
        solver_result = self._optimizer.solve(
            graph=graph,
            edge_params=edge_params,
            drivers=drivers,
            origin_node=origin_node,
            dest_node=dest_node,
            weights=normalized_weights,
            constraints=config.DEFAULT_CONSTRAINTS,
            physics=physics,
        )

        # 7. Assemble the route
        route = self._assembler.assemble(
            result=solver_result,
            origin_geo=origin,
            destination_geo=destination,
            origin_node=origin_node,
            dest_node=dest_node,
            scenario=scenario_type,
            weights=weights,
        )

        # 8. Persist for thesis analysis
        await self._persistence.save_route_result(route)

        return route
