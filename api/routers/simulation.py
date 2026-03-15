from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_scenario_service
from api.schemas.simulation import ScenarioRequestSchema
from core.services.scenario_service import ScenarioService
from domain.enums import ScenarioType

router = APIRouter(prefix="/api/v1", tags=["Simulation"])


@router.post("/simulation/scenario")
async def set_scenario(
    body: ScenarioRequestSchema,
    service: ScenarioService = Depends(get_scenario_service),
):
    try:
        scenario_type = ScenarioType(body.scenario)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid scenario: {body.scenario}. "
            f"Valid: {[s.value for s in ScenarioType]}",
        )

    scenario_id, physics = await service.set_scenario(scenario_type)

    return {
        "message": f"Scenario changed to {scenario_type.value}.",
        "scenario_id": scenario_id,
        "physics": {
            "speed_multiplier": physics.speed_multiplier,
            "demand_multiplier": physics.demand_multiplier,
            "emission_multiplier": physics.emission_multiplier,
            "capacity_multiplier": physics.capacity_multiplier,
        },
    }
