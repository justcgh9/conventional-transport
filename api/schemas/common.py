from pydantic import BaseModel, Field


class GeoPointSchema(BaseModel):
    lat: float = Field(..., example=55.7539)
    lon: float = Field(..., example=48.7432)


class UserWeightsSchema(BaseModel):
    w_time: float = Field(0.4, ge=0.0, le=1.0)
    w_cost: float = Field(0.3, ge=0.0, le=1.0)
    w_emissions: float = Field(0.2, ge=0.0, le=1.0)
    w_comfort: float = Field(0.1, ge=0.0, le=1.0)
