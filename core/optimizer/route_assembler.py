"""
Converts raw SolverResult into the Route domain entity.
Handles:
  - Ordering edges into a path
  - Merging consecutive same-mode edges into segments
  - Prepending/appending walk segments
  - Computing aggregate metrics
  - Counting multi-leg trips (mode switches)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from core.ports.graph_port import GraphPort
from domain.enums import TransportMode, SolverStatus, ScenarioType
from domain.route import Route, RouteSegment
from domain.value_objects import (
    EdgeParameters,
    GeoPoint,
    RouteMetrics,
    UserWeights,
)
from core.optimizer.engine import SolverResult
import config


class RouteAssembler:

    def __init__(self, graph_port: GraphPort):
        self._graph = graph_port

    def assemble(
        self,
        result: SolverResult,
        origin_geo: GeoPoint,
        destination_geo: GeoPoint,
        origin_node: int,
        dest_node: int,
        scenario: ScenarioType,
        weights: UserWeights,
    ) -> Route:

        if result.status != SolverStatus.OPTIMAL:
            return Route(
                status=result.status,
                metrics=RouteMetrics(solve_time_s=result.solve_time_s),
                segments=[],
                origin=origin_geo,
                destination=destination_geo,
                scenario=scenario,
                weights_used=weights,
            )

        # --- 1. Build ordered edge list with modes ---
        ordered = self._order_edges(
            result.active_car_edges,
            result.active_scooter_edges,
            origin_node,
            dest_node,
        )

        # --- 2. Merge consecutive same-mode edges into segments ---
        segments = self._merge_into_segments(ordered, result.edge_params_used)

        # --- 3. Prepend walk from user GPS to origin node ---
        origin_node_geo = self._graph.get_node_coords(origin_node)
        walk_to_origin = self._make_walk_segment(
            origin_geo, origin_node_geo, "Walk to start point"
        )
        if walk_to_origin.distance_km > 0.01:
            segments.insert(0, walk_to_origin)

        # --- 4. Append walk from dest node to user GPS ---
        dest_node_geo = self._graph.get_node_coords(dest_node)
        walk_from_dest = self._make_walk_segment(
            dest_node_geo, destination_geo, "Walk to destination"
        )
        if walk_from_dest.distance_km > 0.01:
            segments.append(walk_from_dest)

        # --- 5. Compute aggregate metrics ---
        metrics = self._compute_metrics(segments, result)

        return Route(
            status=SolverStatus.OPTIMAL,
            metrics=metrics,
            segments=segments,
            origin=origin_geo,
            destination=destination_geo,
            scenario=scenario,
            weights_used=weights,
        )

    def _order_edges(
        self,
        car_edges: List[Tuple[int, int]],
        scooter_edges: List[Tuple[int, int]],
        origin: int,
        dest: int,
    ) -> List[Tuple[int, int, TransportMode]]:
        """Reconstruct the ordered path from unordered edge sets."""

        edge_mode = {}
        for u, v in car_edges:
            edge_mode[(u, v)] = TransportMode.CARPOOL
        for u, v in scooter_edges:
            edge_mode[(u, v)] = TransportMode.SCOOTER

        # Build adjacency from active edges
        adj: Dict[int, Tuple[int, TransportMode]] = {}
        for (u, v), mode in edge_mode.items():
            adj[u] = (v, mode)

        ordered = []
        current = origin
        visited = set()

        while current != dest and current in adj and current not in visited:
            visited.add(current)
            next_node, mode = adj[current]
            ordered.append((current, next_node, mode))
            current = next_node

        return ordered

    def _merge_into_segments(
        self,
        ordered: List[Tuple[int, int, TransportMode]],
        edge_params: Dict[Tuple[int, int], EdgeParameters],
    ) -> List[RouteSegment]:
        """Group consecutive edges with the same mode into segments."""

        if not ordered:
            return []

        segments: List[RouteSegment] = []
        current_mode = ordered[0][2]
        current_edges: List[Tuple[int, int]] = []

        for u, v, mode in ordered:
            if mode != current_mode and current_edges:
                seg = self._build_segment(
                    current_edges, current_mode, edge_params
                )
                segments.append(seg)
                current_edges = []
                current_mode = mode
            current_edges.append((u, v))

        if current_edges:
            seg = self._build_segment(
                current_edges, current_mode, edge_params
            )
            segments.append(seg)

        return segments

    def _build_segment(
        self,
        edges: List[Tuple[int, int]],
        mode: TransportMode,
        edge_params: Dict[Tuple[int, int], EdgeParameters],
    ) -> RouteSegment:

        geometry: List[Tuple[float, float]] = []
        total_dist = 0.0
        total_time = 0.0
        total_emissions = 0.0
        satisfaction_sum = 0.0

        for u, v in edges:
            # Add geometry
            try:
                edge_geo = self._graph.get_edge_geometry(u, v)
                geometry.extend(edge_geo)
            except Exception:
                u_c = self._graph.get_node_coords(u)
                v_c = self._graph.get_node_coords(v)
                geometry.append((u_c.lat, u_c.lon))
                geometry.append((v_c.lat, v_c.lon))

            p = edge_params.get((u, v))
            if p is None:
                continue

            total_dist += p.distance_km

            if mode == TransportMode.CARPOOL:
                total_time += p.car_time_min
                total_emissions += p.car_emission_g
                satisfaction_sum += p.car_satisfaction
            else:
                total_time += p.scooter_time_min
                total_emissions += p.scooter_emission_g
                satisfaction_sum += p.scooter_satisfaction

        avg_satisfaction = satisfaction_sum / len(edges) if edges else 0.0

        mode_label = "carpooling" if mode == TransportMode.CARPOOL else "scooter"
        instruction = f"Ride {mode_label} for {total_dist:.1f} km"

        return RouteSegment(
            mode=mode,
            geometry=geometry,
            distance_km=total_dist,
            duration_min=total_time,
            emissions_g=total_emissions,
            satisfaction=avg_satisfaction,
            instruction=instruction,
        )

    def _make_walk_segment(
        self, start: GeoPoint, end: GeoPoint, instruction: str
    ) -> RouteSegment:
        from geopy.distance import geodesic

        dist_km = (
            geodesic((start.lat, start.lon), (end.lat, end.lon)).km
        )
        time_min = (dist_km / config.WALK_SPEED_KMH) * 60.0

        return RouteSegment(
            mode=TransportMode.WALK,
            geometry=[(start.lat, start.lon), (end.lat, end.lon)],
            distance_km=dist_km,
            duration_min=time_min,
            emissions_g=0.0,
            satisfaction=7.0,
            instruction=instruction,
        )

    def _compute_metrics(
        self, segments: List[RouteSegment], result: SolverResult
    ) -> RouteMetrics:

        total_time = sum(s.duration_min for s in segments)
        total_cost = 0.0
        total_emissions = sum(s.emissions_g for s in segments)
        satisfactions = [s.satisfaction for s in segments if s.satisfaction > 0]
        avg_satisfaction = (
            sum(satisfactions) / len(satisfactions) if satisfactions else 0.0
        )

        # Count per-mode trips and multi-leg switches
        transport_segments = [
            s for s in segments if s.mode != TransportMode.WALK
        ]
        num_vehicle = sum(
            1 for s in transport_segments if s.mode == TransportMode.CARPOOL
        )
        num_micro = sum(
            1 for s in transport_segments if s.mode == TransportMode.SCOOTER
        )

        # Multi-leg = number of mode switches within transport segments
        num_multileg = 0
        for i in range(1, len(transport_segments)):
            if transport_segments[i].mode != transport_segments[i - 1].mode:
                num_multileg += 1

        # Cost estimation from edge params
        for (u, v), p in result.edge_params_used.items():
            if (u, v) in [
                tuple(e) for e in result.active_car_edges
            ]:
                total_cost += p.car_cost_rub
            elif (u, v) in [
                tuple(e) for e in result.active_scooter_edges
            ]:
                total_cost += p.scooter_cost_rub

        return RouteMetrics(
            total_time_min=total_time,
            total_cost_rub=total_cost,
            total_emissions_g=total_emissions,
            satisfaction_score=avg_satisfaction,
            solve_time_s=result.solve_time_s,
            num_vehicle_trips=num_vehicle,
            num_micromobility_trips=num_micro,
            num_multileg_trips=num_multileg,
        )
