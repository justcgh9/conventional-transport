from __future__ import annotations

from typing import List

from core.ports.vehicle_supply_port import VehicleSupplyPort
from domain.entities import Vehicle


class SupplyService:

    def __init__(self, supply_port: VehicleSupplyPort):
        self._supply = supply_port

    async def get_all_vehicles(self) -> List[Vehicle]:
        return await self._supply.get_all_vehicles()
