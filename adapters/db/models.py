"""SQLAlchemy ORM models — the database schema."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class VehicleRow(Base):
    __tablename__ = "vehicles"

    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    graph_node_id = Column(Integer, nullable=True)
    is_available = Column(Boolean, default=True)
    battery_level = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=True)
    vehicle_class = Column(String, nullable=True)
    cost_per_km = Column(Float, nullable=True)
    emission_rate = Column(Float, nullable=True)
    planned_route = Column(JSONB, nullable=True)
    status = Column(String, default="AVAILABLE")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ScenarioRow(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, nullable=False)
    physics = Column(JSONB, nullable=False)
    activated_at = Column(DateTime, default=func.now())


class RouteCalculationRow(Base):
    __tablename__ = "route_calculations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requested_at = Column(DateTime, default=func.now())
    origin_lat = Column(Float, nullable=False)
    origin_lon = Column(Float, nullable=False)
    dest_lat = Column(Float, nullable=False)
    dest_lon = Column(Float, nullable=False)
    scenario_type = Column(String, nullable=False)
    weights = Column(JSONB, nullable=False)
    status = Column(String, nullable=False)
    total_time_min = Column(Float, nullable=True)
    total_cost_rub = Column(Float, nullable=True)
    total_emissions = Column(Float, nullable=True)
    satisfaction = Column(Float, nullable=True)
    solve_time_s = Column(Float, nullable=True)
    num_vehicle = Column(Integer, nullable=True)
    num_micro = Column(Integer, nullable=True)
    num_multileg = Column(Integer, nullable=True)
    segments = Column(JSONB, nullable=True)
    raw_objective = Column(Float, nullable=True)


class EdgeParameterRow(Base):
    __tablename__ = "edge_parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, nullable=False)
    node_from = Column(Integer, nullable=False)
    node_to = Column(Integer, nullable=False)
    distance_km = Column(Float, nullable=False)
    car_time_min = Column(Float)
    scooter_time_min = Column(Float)
    car_emission_g = Column(Float)
    scooter_emission_g = Column(Float)
    car_satisfaction = Column(Float)
    scooter_satisfaction = Column(Float)
    car_available = Column(Boolean)
    scooter_available = Column(Boolean)
    demand = Column(Float)
    generated_at = Column(DateTime, default=func.now())
