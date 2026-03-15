from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from domain.enums import ScenarioType
from domain.value_objects import ScenarioPhysics, EdgeParameters
from domain.route import Route


class PersistencePort(ABC):

    @abstractmethod
    async def save_route_result(self, route: Route) -> int:
        """Persists a completed route calculation. Returns row ID."""
        ...

    @abstractmethod
    async def save_edge_parameters(
        self, scenario_id: int, params: List[EdgeParameters]
    ) -> None:
        ...

    @abstractmethod
    async def get_active_scenario(self) -> Tuple[ScenarioType, ScenarioPhysics]:
        ...

    @abstractmethod
    async def set_active_scenario(
        self, scenario_type: ScenarioType, physics: ScenarioPhysics
    ) -> int:
        """Returns the scenario row ID."""
        ...

    @abstractmethod
    async def get_route_history(
        self,
        limit: int = 100,
        scenario_filter: Optional[ScenarioType] = None,
    ) -> List[Route]:
        ...
