from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from api.dependencies import get_supply_service
from api.schemas.supply import VehicleListSchema, VehicleSchema
from core.services.supply_service import SupplyService

router = APIRouter(prefix="/api/v1", tags=["Supply"])


@router.get("/supply", response_model=VehicleListSchema)
async def get_supply(
    service: SupplyService = Depends(get_supply_service),
):
    vehicles = await service.get_all_vehicles()

    return VehicleListSchema(
        timestamp=datetime.now(timezone.utc),
        vehicles=[
            VehicleSchema(
                id=v.id,
                type=v.type.value,
                lat=v.location.lat,
                lon=v.location.lon,
                status=v.status.value,
            )
            for v in vehicles
        ],
    )
