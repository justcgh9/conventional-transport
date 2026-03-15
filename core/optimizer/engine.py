"""
The mathematical optimization engine.
Implements the MILP formulation from Imbugwa et al., Sections 2.5-2.7.

Decision variables:
    x_ij ∈ {0,1}  — carpool on edge (i,j)       [paper: x_ij]
    y_ij ∈ {0,1}  — micromobility on edge (i,j)  [paper: y_ij]
    z_v  ∈ {0,1}  — vehicle v is activated        [paper: z_v]

Objective: Eq. 5
Constraints: Sections 2.6.1–2.6.4 + flow conservation
Solver: PuLP / CBC (same as paper, Section 2.7)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pulp
import networkx as nx

from domain.entities import CarpoolDriver
from domain.enums import SolverStatus
from domain.value_objects import (
    ConstraintConfig,
    EdgeParameters,
    ScenarioPhysics,
    UserWeights,
)
import config as cfg


@dataclass
class SolverResult:
    status: SolverStatus
    objective_value: float = 0.0
    solve_time_s: float = 0.0
    active_car_edges: List[Tuple[int, int]] = field(default_factory=list)
    active_scooter_edges: List[Tuple[int, int]] = field(default_factory=list)
    active_vehicle_ids: List[str] = field(default_factory=list)
    edge_params_used: Dict[Tuple[int, int], EdgeParameters] = field(
        default_factory=dict
    )


class OptimizerEngine:
    """
    Constructs and solves the PuLP MILP problem as defined in the paper.
    """

    def solve(
        self,
        graph: nx.DiGraph,
        edge_params: Dict[Tuple[int, int], EdgeParameters],
        drivers: List[CarpoolDriver],
        origin_node: int,
        dest_node: int,
        weights: UserWeights,
        constraints: Optional[ConstraintConfig] = None,
        physics: Optional[ScenarioPhysics] = None,
    ) -> SolverResult:

        if constraints is None:
            constraints = cfg.DEFAULT_CONSTRAINTS

        w = weights.normalized()
        start = time.perf_counter()

        prob = pulp.LpProblem("Multimodal_Routing", pulp.LpMinimize)

        # ---------------------------------------------------------------
        # Decision Variables
        # ---------------------------------------------------------------
        edges = list(graph.edges())

        x: Dict[Tuple[int, int], pulp.LpVariable] = {}
        y: Dict[Tuple[int, int], pulp.LpVariable] = {}

        for u, v in edges:
            x[(u, v)] = pulp.LpVariable(f"x_{u}_{v}", cat=pulp.LpBinary)
            y[(u, v)] = pulp.LpVariable(f"y_{u}_{v}", cat=pulp.LpBinary)

        # z_v: one per carpool driver
        z: Dict[str, pulp.LpVariable] = {}
        for d in drivers:
            z[d.id] = pulp.LpVariable(f"z_{d.id}", cat=pulp.LpBinary)

        # ---------------------------------------------------------------
        # Objective Function — Paper Eq. 5
        # Minimize: λ1·T + λ2·C + λ3·E - λ4·S
        # ---------------------------------------------------------------

        # Term 1: Travel Time (Eq. 1)
        obj_time = []
        for u, v in edges:
            p = edge_params.get((u, v))
            if p is None:
                continue
            obj_time.append(p.car_time_min * x[(u, v)])
            obj_time.append(p.scooter_time_min * y[(u, v)])

        # Term 2: Cost (Eq. 2)
        obj_cost = []
        # Vehicle activation costs
        for d in drivers:
            # C_v approximated as cost_per_km * avg trip distance
            avg_dist = 2.0  # km, rough estimate for per-activation cost
            obj_cost.append(d.cost_per_km * avg_dist * z[d.id])
        # Micromobility costs per edge
        for u, v in edges:
            p = edge_params.get((u, v))
            if p is None:
                continue
            obj_cost.append(p.scooter_cost_rub * y[(u, v)])

        # Term 3: Emissions (Eq. 3)
        obj_emissions = []
        for d in drivers:
            avg_dist = 2.0
            obj_emissions.append(
                d.emission_rate_g_km * avg_dist * z[d.id]
            )
        for u, v in edges:
            p = edge_params.get((u, v))
            if p is None:
                continue
            obj_emissions.append(p.scooter_emission_g * y[(u, v)])

        # Term 4: Satisfaction (Eq. 4) — negated because we maximize
        obj_satisfaction = []
        for u, v in edges:
            p = edge_params.get((u, v))
            if p is None:
                continue
            obj_satisfaction.append(p.car_satisfaction * x[(u, v)])
            obj_satisfaction.append(p.scooter_satisfaction * y[(u, v)])

        # Combined Objective (Eq. 5)
        prob += (
            w.w_time * pulp.lpSum(obj_time)
            + w.w_cost * pulp.lpSum(obj_cost)
            + w.w_emissions * pulp.lpSum(obj_emissions)
            - w.w_comfort * pulp.lpSum(obj_satisfaction)
        )

        # ---------------------------------------------------------------
        # Constraints
        # ---------------------------------------------------------------

        # C4 (paper 2.6.4): Assignment — at most one mode per edge
        # (becomes exactly one for edges on the path via flow conservation)
        for u, v in edges:
            prob += (
                x[(u, v)] + y[(u, v)] <= 1,
                f"ModeExclusivity_{u}_{v}",
            )

        # C5: Flow Conservation
        nodes = list(graph.nodes())
        for n in nodes:
            out_flow = pulp.lpSum(
                x[(u, v)] + y[(u, v)]
                for u, v in edges
                if u == n
            )
            in_flow = pulp.lpSum(
                x[(u, v)] + y[(u, v)]
                for u, v in edges
                if v == n
            )

            if n == origin_node:
                prob += (out_flow - in_flow == 1, f"FlowOrigin_{n}")
            elif n == dest_node:
                prob += (in_flow - out_flow == 1, f"FlowDest_{n}")
            else:
                prob += (out_flow - in_flow == 0, f"FlowBalance_{n}")

        # C6: Mode Availability
        for u, v in edges:
            p = edge_params.get((u, v))
            if p is None:
                prob += (x[(u, v)] == 0, f"NoParamCar_{u}_{v}")
                prob += (y[(u, v)] == 0, f"NoParamScooter_{u}_{v}")
                continue

            if not p.car_available:
                prob += (x[(u, v)] == 0, f"CarUnavail_{u}_{v}")
            if not p.scooter_available:
                prob += (y[(u, v)] == 0, f"ScooterUnavail_{u}_{v}")

        # C2 (paper 2.6.2): Travel Time Limits
        for u, v in edges:
            p = edge_params.get((u, v))
            if p is None:
                continue
            prob += (
                p.car_time_min * x[(u, v)] <= constraints.t_max_min,
                f"CarTimeLimit_{u}_{v}",
            )
            prob += (
                p.scooter_time_min * y[(u, v)] <= constraints.m_max_min,
                f"ScooterTimeLimit_{u}_{v}",
            )

        # C3 (paper 2.6.3): Emissions Cap
        all_emissions = []
        for d in drivers:
            avg_dist = 2.0
            all_emissions.append(d.emission_rate_g_km * avg_dist * z[d.id])
        for u, v in edges:
            p = edge_params.get((u, v))
            if p is None:
                continue
            all_emissions.append(p.scooter_emission_g * y[(u, v)])
        prob += (
            pulp.lpSum(all_emissions) <= constraints.e_max_g,
            "EmissionsCap",
        )

        # C1 (paper 2.6.1): Vehicle Capacity
        cap_mult = physics.capacity_multiplier if physics else 1.0
        for d in drivers:
            relevant_demand = pulp.lpSum(
                edge_params[(u, v)].demand * x[(u, v)]
                for u, v in edges
                if (u, v) in edge_params
            )
            prob += (
                relevant_demand
                <= d.capacity * cap_mult + (1 - z[d.id]) * 10000,
                f"Capacity_{d.id}",
            )

        # C7: Vehicle activation linking
        # If any car edge is used, at least one vehicle must be active
        total_car_usage = pulp.lpSum(x[(u, v)] for u, v in edges)
        total_z = pulp.lpSum(z[d.id] for d in drivers) if drivers else 0
        if drivers:
            prob += (
                total_car_usage <= total_z * len(edges),
                "VehicleActivation",
            )

        # ---------------------------------------------------------------
        # Solve
        # ---------------------------------------------------------------
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=30)
        prob.solve(solver)

        elapsed = time.perf_counter() - start

        # ---------------------------------------------------------------
        # Extract Results
        # ---------------------------------------------------------------
        status_str = pulp.LpStatus.get(prob.status, "Error")
        if status_str == "Optimal":
            status = SolverStatus.OPTIMAL
        elif status_str == "Infeasible":
            status = SolverStatus.INFEASIBLE
        else:
            status = SolverStatus.ERROR

        result = SolverResult(
            status=status,
            objective_value=pulp.value(prob.objective) or 0.0,
            solve_time_s=elapsed,
            edge_params_used=edge_params,
        )

        if status == SolverStatus.OPTIMAL:
            for u, v in edges:
                if x[(u, v)].varValue and x[(u, v)].varValue > 0.5:
                    result.active_car_edges.append((u, v))
                if y[(u, v)].varValue and y[(u, v)].varValue > 0.5:
                    result.active_scooter_edges.append((u, v))
            for d in drivers:
                if z[d.id].varValue and z[d.id].varValue > 0.5:
                    result.active_vehicle_ids.append(d.id)

        return result
