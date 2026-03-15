from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_routing_service
from api.schemas.routing import (
    RouteMetricsSchema,
    RouteRequestSchema,
    RouteResponseSchema,
    RouteSegmentSchema,
)
from core.services.routing_service import RoutingService
from domain.enums import SolverStatus
from domain.value_objects import GeoPoint, UserWeights

router = APIRouter(prefix="/api/v1", tags=["Routing"])


@router.post("/route/calculate", response_model=RouteResponseSchema)
async def calculate_route(
    body: RouteRequestSchema,
    service: RoutingService = Depends(get_routing_service),
):
    origin = GeoPoint(lat=body.origin.lat, lon=body.origin.lon)
    destination = GeoPoint(lat=body.destination.lat, lon=body.destination.lon)
    weights = UserWeights(
        w_time=body.weights.w_time,
        w_cost=body.weights.w_cost,
        w_emissions=body.weights.w_emissions,
        w_comfort=body.weights.w_comfort,
    )

    route = await service.calculate_route(origin, destination, weights)

    if route.status == SolverStatus.INFEASIBLE:
        raise HTTPException(
            status_code=404,
            detail="No feasible route found. Try relaxing constraints.",
        )
    if route.status == SolverStatus.ERROR:
        raise HTTPException(
            status_code=500,
            detail="Solver encountered an error.",
        )

    return RouteResponseSchema(
        status=route.status.value,
        metrics=RouteMetricsSchema(
            total_time_min=route.metrics.total_time_min,
            total_price_rub=route.metrics.total_cost_rub,
            total_emissions_g=route.metrics.total_emissions_g,
            satisfaction_score=route.metrics.satisfaction_score,
            solve_time_s=route.metrics.solve_time_s,
        ),
        segments=[
            RouteSegmentSchema(
                mode=s.mode.value,
                distance_km=round(s.distance_km, 3),
                duration_min=round(s.duration_min, 2),
                instruction=s.instruction,
                geometry=[[p[0], p[1]] for p in s.geometry],
            )
            for s in route.segments
        ],
    )
