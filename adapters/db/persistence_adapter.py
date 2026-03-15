from __future__ import annotations

import dataclasses
from typing import List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from adapters.db.models import (
    EdgeParameterRow,
    RouteCalculationRow,
    ScenarioRow,
)
from core.ports.persistence_port import PersistencePort
from domain.enums import ScenarioType
from domain.route import Route
from domain.value_objects import EdgeParameters, ScenarioPhysics


class PostgresPersistenceAdapter(PersistencePort):

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save_route_result(self, route: Route) -> int:
        row = RouteCalculationRow(
            origin_lat=route.origin.lat,
            origin_lon=route.origin.lon,
            dest_lat=route.destination.lat,
            dest_lon=route.destination.lon,
            scenario_type=route.scenario.value,
            weights={
                "w_time": route.weights_used.w_time,
                "w_cost": route.weights_used.w_cost,
                "w_emissions": route.weights_used.w_emissions,
                "w_comfort": route.weights_used.w_comfort,
            },
            status=route.status.value,
            total_time_min=route.metrics.total_time_min,
            total_cost_rub=route.metrics.total_cost_rub,
            total_emissions=route.metrics.total_emissions_g,
            satisfaction=route.metrics.satisfaction_score,
            solve_time_s=route.metrics.solve_time_s,
            num_vehicle=route.metrics.num_vehicle_trips,
            num_micro=route.metrics.num_micromobility_trips,
            num_multileg=route.metrics.num_multileg_trips,
            segments=[
                {
                    "mode": s.mode.value,
                    "geometry": s.geometry,
                    "distance_km": s.distance_km,
                    "duration_min": s.duration_min,
                    "emissions_g": s.emissions_g,
                    "instruction": s.instruction,
                }
                for s in route.segments
            ],
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row.id

    async def save_edge_parameters(
        self, scenario_id: int, params: List[EdgeParameters]
    ) -> None:
        rows = [
            EdgeParameterRow(
                scenario_id=scenario_id,
                node_from=p.node_from,
                node_to=p.node_to,
                distance_km=p.distance_km,
                car_time_min=p.car_time_min,
                scooter_time_min=p.scooter_time_min,
                car_emission_g=p.car_emission_g,
                scooter_emission_g=p.scooter_emission_g,
                car_satisfaction=p.car_satisfaction,
                scooter_satisfaction=p.scooter_satisfaction,
                car_available=p.car_available,
                scooter_available=p.scooter_available,
                demand=p.demand,
            )
            for p in params
        ]
        self._session.add_all(rows)
        await self._session.commit()

    async def get_active_scenario(
        self,
    ) -> Tuple[ScenarioType, ScenarioPhysics]:
        stmt = select(ScenarioRow).order_by(desc(ScenarioRow.activated_at)).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            default_type = ScenarioType.NORMAL
            return default_type, config.SCENARIO_PHYSICS[default_type]

        scenario_type = ScenarioType(row.type)
        physics = ScenarioPhysics(**row.physics)
        return scenario_type, physics

    async def set_active_scenario(
        self, scenario_type: ScenarioType, physics: ScenarioPhysics
    ) -> int:
        row = ScenarioRow(
            type=scenario_type.value,
            physics=dataclasses.asdict(physics),
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row.id

    async def get_route_history(
        self,
        limit: int = 100,
        scenario_filter: Optional[ScenarioType] = None,
    ) -> list:
        stmt = select(RouteCalculationRow).order_by(
            desc(RouteCalculationRow.requested_at)
        )
        if scenario_filter:
            stmt = stmt.where(
                RouteCalculationRow.scenario_type == scenario_filter.value
            )
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()
