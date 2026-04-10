"""
Scenario service — manages the active urban scenario.
Delegates storage to the PersistencePort so the active scenario
survives across request instances.
"""
from __future__ import annotations

import uuid

import config
from core.ports.persistence_port import PersistencePort
from domain.enums import ScenarioType
from domain.value_objects import ScenarioPhysics


class ScenarioService:
    def __init__(self, persistence: PersistencePort) -> None:
        self._persistence = persistence

    async def get_active(self) -> tuple[ScenarioType, ScenarioPhysics]:
        """Return the currently active scenario type and its physics."""
        try:
            scenario_type, physics = await self._persistence.get_active_scenario()
            return scenario_type, physics
        except Exception:
            # Fall back to NORMAL if nothing has been persisted yet
            scenario_type = ScenarioType.NORMAL
            physics = config.SCENARIO_PHYSICS[scenario_type]
            return scenario_type, physics

    async def set_scenario(
        self, scenario_type: ScenarioType
    ) -> tuple[str, ScenarioPhysics]:
        """
        Activate a new scenario.

        Returns a (scenario_id, physics) tuple where scenario_id is a
        string UUID that the API layer can return to the caller.
        """
        physics = config.SCENARIO_PHYSICS[scenario_type]
        await self._persistence.set_active_scenario(scenario_type, physics)
        scenario_id = str(uuid.uuid4())
        return scenario_id, physics
