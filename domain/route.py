from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from domain.enums import TransportMode, SolverStatus, ScenarioType
from domain.value_objects import GeoPoint, UserWeights, RouteMetrics


@dataclass
class RouteSegment:
    mode: TransportMode
    geometry: List[Tuple[float, float]]
    distance_km: float = 0.0
    duration_min: float = 0.0
    emissions_g: float = 0.0
    satisfaction: float = 0.0
    instruction: str = ""
    vehicle_id: Optional[str] = None


@dataclass
class Route:
    status: SolverStatus
    metrics: RouteMetrics
    segments: List[RouteSegment]
    origin: GeoPoint
    destination: GeoPoint
    scenario: ScenarioType
    weights_used: UserWeights
    timestamp: datetime = field(default_factory=datetime.utcnow)
