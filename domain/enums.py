from enum import Enum


class VehicleType(str, Enum):
    SCOOTER = "SCOOTER"
    CARPOOL_DRIVER = "CARPOOL_DRIVER"


class TransportMode(str, Enum):
    WALK = "WALK"
    SCOOTER = "SCOOTER"
    CARPOOL = "CARPOOL"


class ScenarioType(str, Enum):
    NORMAL = "NORMAL"
    MORNING_PEAK = "MORNING_PEAK"
    EVENING_OFFPEAK = "EVENING_OFFPEAK"
    RAINY_WEATHER = "RAINY_WEATHER"
    CITY_EVENT = "CITY_EVENT"
    MAJOR_ACCIDENT = "MAJOR_ACCIDENT"


class SolverStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    INFEASIBLE = "INFEASIBLE"
    ERROR = "ERROR"


class VehicleStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    LOW_BATTERY = "LOW_BATTERY"
