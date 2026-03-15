from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float


@dataclass(frozen=True)
class UserWeights:
    """Maps to lambda_1 through lambda_4 in Eq. 5 of the paper."""

    w_time: float = 0.4
    w_cost: float = 0.3
    w_emissions: float = 0.2
    w_comfort: float = 0.1

    def normalized(self) -> UserWeights:
        total = self.w_time + self.w_cost + self.w_emissions + self.w_comfort
        if total == 0:
            return UserWeights(0.25, 0.25, 0.25, 0.25)
        return UserWeights(
            w_time=self.w_time / total,
            w_cost=self.w_cost / total,
            w_emissions=self.w_emissions / total,
            w_comfort=self.w_comfort / total,
        )


@dataclass(frozen=True)
class ScenarioPhysics:
    """
    Encodes the dynamic parameter adjustments from paper Section 2.2.
    All multipliers are applied to base values during edge parameter generation.
    """

    speed_multiplier: float = 1.0
    demand_multiplier: float = 1.0
    emission_multiplier: float = 1.0
    capacity_multiplier: float = 1.0
    base_car_speed_kmh: float = 45.0
    sigma_travel_time: float = 0.2


@dataclass(frozen=True)
class RouteMetrics:
    total_time_min: float = 0.0
    total_cost_rub: float = 0.0
    total_emissions_g: float = 0.0
    satisfaction_score: float = 0.0
    solve_time_s: float = 0.0
    num_vehicle_trips: int = 0
    num_micromobility_trips: int = 0
    num_multileg_trips: int = 0


@dataclass(frozen=True)
class EdgeParameters:
    """All computed parameters for a single directed edge (i -> j)."""

    node_from: int
    node_to: int
    distance_km: float

    # Car mode parameters (maps to x_ij)
    car_time_min: float = 0.0
    car_cost_rub: float = 0.0
    car_emission_g: float = 0.0
    car_satisfaction: float = 0.0
    car_available: bool = False

    # Scooter mode parameters (maps to y_ij)
    scooter_time_min: float = 0.0
    scooter_cost_rub: float = 0.0
    scooter_emission_g: float = 0.0
    scooter_satisfaction: float = 0.0
    scooter_available: bool = False

    # Demand
    demand: float = 1.0

    # Variance of car travel time (needed for satisfaction penalty)
    car_time_variance: float = 0.0
    scooter_time_variance: float = 0.0


@dataclass(frozen=True)
class ConstraintConfig:
    """System-level limits from paper Section 2.6."""

    t_max_min: float = 60.0
    m_max_min: float = 45.0
    e_max_g: float = 5000.0
