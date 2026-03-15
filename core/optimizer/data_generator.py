"""
Implements the synthetic data generation framework from paper Section 3.2.
Travel times:  Log-normal distribution (Section 3.2.1, Eq. 1)
Emissions:     Rate-based calculation (Section 3.2.2, Table 1)
Satisfaction:  Beta distribution * reliability penalty (Section 3.2.3, Eq. 2)
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from scipy import stats

import config
from domain.entities import CarpoolDriver, Scooter
from domain.value_objects import EdgeParameters, ScenarioPhysics

import networkx as nx


class EdgeParameterGenerator:
    """
    Generates stochastic edge parameters for the optimization model.
    Called once per scenario activation, not per route request.
    """

    def __init__(self, rng_seed: Optional[int] = None):
        self._rng = np.random.default_rng(rng_seed)

    def generate(
        self,
        graph: nx.DiGraph,
        physics: ScenarioPhysics,
        scooters: List[Scooter],
        drivers: List[CarpoolDriver],
    ) -> Dict[Tuple[int, int], EdgeParameters]:
        """
        Generates EdgeParameters for every edge in the graph,
        incorporating the current scenario physics and vehicle supply.
        """

        # Pre-compute which nodes have scooters nearby
        scooter_nodes: Set[int] = set()
        for s in scooters:
            if s.graph_node_id is not None:
                scooter_nodes.add(s.graph_node_id)

        # Pre-compute which edges are covered by carpool drivers
        driver_edges: Set[Tuple[int, int]] = set()
        for d in drivers:
            if d.planned_route and len(d.planned_route) >= 2:
                for i in range(len(d.planned_route) - 1):
                    driver_edges.add(
                        (d.planned_route[i], d.planned_route[i + 1])
                    )

        # Average driver cost and emission rate for the objective function
        avg_driver_cost = (
            np.mean([d.cost_per_km for d in drivers])
            if drivers
            else config.CAR_COST_RUB_KM
        )
        avg_driver_emission = (
            np.mean([d.emission_rate_g_km for d in drivers])
            if drivers
            else config.EMISSION_GASOLINE_CAR_G_KM
        )

        result: Dict[Tuple[int, int], EdgeParameters] = {}

        for u, v, data in graph.edges(data=True):
            d_km = data.get("distance", data.get("length", 100) / 1000.0)

            # --- Car travel time: Paper Eq. 1, Section 3.2.1 ---
            # t_ij = d_ij / exp(N(ln(S), sigma^2))
            S = physics.base_car_speed_kmh * physics.speed_multiplier
            sigma = physics.sigma_travel_time

            # Sample effective speed from log-normal
            ln_S = math.log(max(S, 1.0))
            effective_speed = self._rng.lognormal(mean=ln_S, sigma=sigma)
            effective_speed = max(effective_speed, 1.0)  # Prevent div by zero

            car_time_min = (d_km / effective_speed) * 60.0

            # Variance of car travel time (analytical for log-normal)
            # Var[t] = (d/S)^2 * (exp(sigma^2) - 1) * exp(sigma^2)
            mean_time = (d_km / S) * 60.0 if S > 0 else 60.0
            car_time_var = (
                mean_time ** 2
                * (math.exp(sigma ** 2) - 1)
                * math.exp(sigma ** 2)
            )

            # --- Scooter travel time ---
            scooter_speed = (
                config.SCOOTER_SPEED_KMH * physics.speed_multiplier
            )
            scooter_speed = max(scooter_speed, 1.0)
            scooter_time_min = (d_km / scooter_speed) * 60.0
            scooter_time_var = 0.01  # Low variance (deterministic-ish)

            # --- Costs ---
            car_cost = d_km * avg_driver_cost
            scooter_cost = d_km * config.SCOOTER_COST_RUB_KM

            # --- Emissions: Paper Section 3.2.2 ---
            car_emission = (
                d_km * avg_driver_emission * physics.emission_multiplier
            )
            scooter_emission = (
                d_km * config.EMISSION_SCOOTER_G_KM * physics.emission_multiplier
            )

            # --- Satisfaction: Paper Eq. 2, Section 3.2.3 ---
            # S_ij = 10 * Beta(alpha, beta) * exp(-sigma_ij^2 / sigma_ref^2)
            car_comfort = self._rng.beta(
                config.SAT_ALPHA_CAR, config.SAT_BETA_CAR
            )
            car_reliability = math.exp(
                -car_time_var / config.SAT_SIGMA_REF_SQUARED
            )
            car_satisfaction = config.SAT_SCALE * car_comfort * car_reliability

            scooter_comfort = self._rng.beta(
                config.SAT_ALPHA_SCOOTER, config.SAT_BETA_SCOOTER
            )
            scooter_reliability = math.exp(
                -scooter_time_var / config.SAT_SIGMA_REF_SQUARED
            )
            scooter_satisfaction = (
                config.SAT_SCALE * scooter_comfort * scooter_reliability
            )

            # --- Availability ---
            car_available = (u, v) in driver_edges or len(drivers) > 0
            scooter_available = u in scooter_nodes

            # --- Demand: log-normal ---
            demand = self._rng.lognormal(
                mean=math.log(config.BASE_DEMAND_MEAN),
                sigma=config.BASE_DEMAND_VARIANCE,
            )
            demand *= physics.demand_multiplier

            result[(u, v)] = EdgeParameters(
                node_from=u,
                node_to=v,
                distance_km=d_km,
                car_time_min=car_time_min,
                car_cost_rub=car_cost,
                car_emission_g=car_emission,
                car_satisfaction=car_satisfaction,
                car_available=car_available,
                scooter_time_min=scooter_time_min,
                scooter_cost_rub=scooter_cost,
                scooter_emission_g=scooter_emission,
                scooter_satisfaction=scooter_satisfaction,
                scooter_available=scooter_available,
                demand=demand,
                car_time_variance=car_time_var,
                scooter_time_variance=scooter_time_var,
            )

        return result
