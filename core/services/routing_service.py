"""
Main orchestrator for route calculation.
Coordinates all ports and the optimizer.
"""

from __future__ import annotations

import networkx as nx

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

# Maximum number of edges to pass to the MILP solver.
# The full Innopolis graph has ~420 edges which makes the MILP very slow.
# We restrict to a corridor around the shortest path instead.
_MAX_SUBGRAPH_EDGES = 80


def _build_corridor_subgraph(
    graph: nx.MultiDiGraph,
    origin_node: int,
    dest_node: int,
    max_edges: int = _MAX_SUBGRAPH_EDGES,
) -> nx.MultiDiGraph:
    """
    Return a subgraph containing only nodes/edges that lie on or near the
    shortest path from origin to dest.  This keeps the MILP tractable while
    still giving the optimizer meaningful routing choices.

    Strategy:
      1. Find the shortest path (by distance).
      2. Collect all nodes within 1 hop of any path node.
      3. Return the induced subgraph on those nodes, deduplicated.
    """
    try:
        path_nodes = nx.shortest_path(
            graph, origin_node, dest_node, weight="distance"
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        # Fall back to just the path nodes if no path exists
        return graph.subgraph([origin_node, dest_node]).copy()

    # Expand corridor: include neighbours of path nodes
    corridor_nodes: set[int] = set(path_nodes)
    for n in list(path_nodes):
        corridor_nodes.update(graph.predecessors(n))
        corridor_nodes.update(graph.successors(n))

    sub = graph.subgraph(corridor_nodes).copy()

    # If still too large, trim to just the path nodes + immediate neighbours
    if sub.number_of_edges() > max_edges:
        sub = graph.subgraph(set(path_nodes)).copy()

    return sub


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

        # 3. Get the full simplified graph, then restrict to a corridor
        full_graph = self._graph.get_graph()
        graph = _build_corridor_subgraph(full_graph, origin_node, dest_node)

        # Verify origin and dest are reachable in the subgraph
        has_path = nx.has_path(graph, origin_node, dest_node)
        print(
            f"[ROUTE] origin={origin_node} dest={dest_node} "
            f"same={origin_node == dest_node} "
            f"has_path={has_path} "
            f"subgraph: {graph.number_of_nodes()} nodes, "
            f"{graph.number_of_edges()} edges "
            f"(full: {full_graph.number_of_nodes()} nodes, "
            f"{full_graph.number_of_edges()} edges)"
        )

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

        print(
            f"[ROUTE] Solver status: {solver_result.status.value}, "
            f"objective: {solver_result.objective_value:.4f}, "
            f"time: {solver_result.solve_time_s:.2f}s"
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
