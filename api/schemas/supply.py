from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class VehicleSchema(BaseModel):
    id: str
    type: str
    lat: float
    lon: float
    battery_level: Optional[int] = None
    status: str = "AVAILABLE"


class VehicleListSchema(BaseModel):
    timestamp: datetime
    vehicles: List[VehicleSchema]
