from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List

from domain.enums import VehicleType, VehicleStatus
from domain.value_objects import GeoPoint


@dataclass
class Vehicle:
    id: str
    type: VehicleType
    location: GeoPoint
    graph_node_id: Optional[int] = None
    is_available: bool = True
    status: VehicleStatus = VehicleStatus.AVAILABLE


@dataclass
class Scooter(Vehicle):
    battery_level: int = 100

    def __post_init__(self):
        self.type = VehicleType.SCOOTER


@dataclass
class CarpoolDriver(Vehicle):
    capacity: int = 3
    cost_per_km: float = 15.0
    emission_rate_g_km: float = 204.0
    vehicle_class: str = "gasoline"
    planned_route: Optional[List[int]] = None
    departure_time: Optional[str] = None

    def __post_init__(self):
        self.type = VehicleType.CARPOOL_DRIVER
