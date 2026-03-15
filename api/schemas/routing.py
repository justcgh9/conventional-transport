from typing import List, Tuple

from pydantic import BaseModel

from api.schemas.common import GeoPointSchema, UserWeightsSchema


class RouteRequestSchema(BaseModel):
    origin: GeoPointSchema
    destination: GeoPointSchema
    weights: UserWeightsSchema


class RouteMetricsSchema(BaseModel):
    total_time_min: float
    total_price_rub: float
    total_emissions_g: float
    satisfaction_score: float
    solve_time_s: float = 0.0


class RouteSegmentSchema(BaseModel):
    mode: str
    distance_km: float
    duration_min: float
    instruction: str
    geometry: List[List[float]]


class RouteResponseSchema(BaseModel):
    status: str
    metrics: RouteMetricsSchema
    segments: List[RouteSegmentSchema]
