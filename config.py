"""
All physics constants and configuration values.
Every number here is traceable to a specific section of the Imbugwa et al. paper.
"""

from __future__ import annotations

from domain.enums import ScenarioType
from domain.value_objects import ScenarioPhysics, ConstraintConfig


# ---------------------------------------------------------------------------
# Speeds (km/h) — Paper Section 3.2.1
# ---------------------------------------------------------------------------
WALK_SPEED_KMH = 5.0
SCOOTER_SPEED_KMH = 15.0
CAR_SPEED_OFFPEAK_KMH = 45.0  # S for off-peak
CAR_SPEED_PEAK_KMH = 25.0  # S for peak

# ---------------------------------------------------------------------------
# Emissions (g CO2 / km) — Paper Table 1
# ---------------------------------------------------------------------------
EMISSION_GASOLINE_CAR_G_KM = 204.0
EMISSION_DIESEL_BUS_G_KM = 2000.0
EMISSION_ELECTRIC_CAR_G_KM = 67.0
EMISSION_EBIKE_G_KM = 6.0
EMISSION_SCOOTER_G_KM = 6.0  # E-bike class from Table 1

# ---------------------------------------------------------------------------
# Costs (RUB / km) — Estimated for Innopolis
# ---------------------------------------------------------------------------
CAR_COST_RUB_KM = 15.0
SCOOTER_COST_RUB_KM = 5.0

# ---------------------------------------------------------------------------
# User Satisfaction — Paper Section 3.2.3, Eq. 2
# Beta distribution parameters (alpha, beta)
# ---------------------------------------------------------------------------
SAT_ALPHA_CAR = 8.0
SAT_BETA_CAR = 2.0
SAT_ALPHA_SCOOTER = 9.0
SAT_BETA_SCOOTER = 1.0
SAT_SCALE = 10.0  # Maximum satisfaction score

# Variance reference for reliability penalty in Eq. 2
SAT_SIGMA_REF_SQUARED = 0.1

# ---------------------------------------------------------------------------
# Vehicle Fleet — Paper Appendix A.1, step 4
# Probabilities: [Gasoline, Diesel Bus, Electric, E-bike]
# ---------------------------------------------------------------------------
VEHICLE_TYPE_PROBABILITIES = [0.55, 0.25, 0.15, 0.05]

# ---------------------------------------------------------------------------
# Demand — Paper Section 3.2
# ---------------------------------------------------------------------------
BASE_DEMAND_MEAN = 5.0
BASE_DEMAND_VARIANCE = 0.5

# ---------------------------------------------------------------------------
# Constraints — Paper Section 2.6
# ---------------------------------------------------------------------------
DEFAULT_CONSTRAINTS = ConstraintConfig(
    t_max_min=60.0,
    m_max_min=45.0,
    e_max_g=5000.0,
)

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
NUM_SCOOTERS = 25
NUM_CARPOOL_DRIVERS = 15
SCOOTER_WALK_RADIUS_M = 300.0
DRIVER_MOVE_INTERVAL_S = 5
DEFAULT_CARPOOL_CAPACITY = 3

# ---------------------------------------------------------------------------
# Geospatial
# ---------------------------------------------------------------------------
INNOPOLIS_CENTER_LAT = 55.7523
INNOPOLIS_CENTER_LON = 48.7445
GRAPH_LOAD_RADIUS_M = 2500

# ---------------------------------------------------------------------------
# Scenario Physics — Paper Section 2.2
# Values directly from the text:
#   Peak:     -30% speed, demand × 2.5
#   Off-peak: baseline speed, demand × 0.5
#   Weather:  -50% speed, +30% emissions
#   Accident: -70% speed, -30% capacity
# ---------------------------------------------------------------------------
SCENARIO_PHYSICS: dict[ScenarioType, ScenarioPhysics] = {
    ScenarioType.NORMAL: ScenarioPhysics(
        speed_multiplier=1.0,
        demand_multiplier=1.0,
        emission_multiplier=1.0,
        capacity_multiplier=1.0,
        base_car_speed_kmh=CAR_SPEED_OFFPEAK_KMH,
        sigma_travel_time=0.2,
    ),
    ScenarioType.MORNING_PEAK: ScenarioPhysics(
        speed_multiplier=0.70,
        demand_multiplier=2.5,
        emission_multiplier=1.0,
        capacity_multiplier=1.0,
        base_car_speed_kmh=CAR_SPEED_PEAK_KMH,
        sigma_travel_time=0.3,
    ),
    ScenarioType.EVENING_OFFPEAK: ScenarioPhysics(
        speed_multiplier=1.0,
        demand_multiplier=0.5,
        emission_multiplier=1.0,
        capacity_multiplier=1.0,
        base_car_speed_kmh=CAR_SPEED_OFFPEAK_KMH,
        sigma_travel_time=0.2,
    ),
    ScenarioType.RAINY_WEATHER: ScenarioPhysics(
        speed_multiplier=0.50,
        demand_multiplier=1.0,
        emission_multiplier=1.3,
        capacity_multiplier=1.0,
        base_car_speed_kmh=CAR_SPEED_PEAK_KMH,
        sigma_travel_time=0.3,
    ),
    ScenarioType.CITY_EVENT: ScenarioPhysics(
        speed_multiplier=0.80,
        demand_multiplier=2.0,
        emission_multiplier=1.0,
        capacity_multiplier=1.0,
        base_car_speed_kmh=30.0,
        sigma_travel_time=0.25,
    ),
    ScenarioType.MAJOR_ACCIDENT: ScenarioPhysics(
        speed_multiplier=0.30,
        demand_multiplier=1.0,
        emission_multiplier=1.0,
        capacity_multiplier=0.70,
        base_car_speed_kmh=CAR_SPEED_PEAK_KMH,
        sigma_travel_time=0.3,
    ),
}
