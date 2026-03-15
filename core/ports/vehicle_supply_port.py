from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities import Vehicle, Scooter, CarpoolDriver


class VehicleSupplyPort(ABC):

    @abstractmethod
    async def get_available_scooters(self) -> List[Scooter]:
        """Returns all scooters that are currently available."""
        ...

    @abstractmethod
    async def get_available_drivers(
        self,
        origin_node: Optional[int] = None,
        dest_node: Optional[int] = None,
    ) -> List[CarpoolDriver]:
        """
        Returns carpool drivers whose routes are compatible
        with the requested origin and destination.
        """
        ...

    @abstractmethod
    async def get_all_vehicles(self) -> List[Vehicle]:
        """Returns all vehicles for the supply endpoint."""
        ...

    @abstractmethod
    async def update_vehicle_status(
        self, vehicle_id: str, is_available: bool
    ) -> None:
        ...
