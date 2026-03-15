"""
Simulated vehicle supply adapter.
Seeds scooters and carpool drivers into PostgreSQL at startup.
Implements VehicleSupplyPort — can be swapped for an external API adapter.
"""

from __future__ import annotations

import random
from typing import List, Optional

import networkx as nx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import config
from adapters.db.models import VehicleRow
from core.ports.graph_port import GraphPort
from core.ports.vehicle_supply_port import VehicleSupplyPort
from domain.entities import CarpoolDriver, Scooter, Vehicle
from domain.enums import VehicleStatus, VehicleType
from domain.value_objects import GeoPoint


class SimulatedSupplyAdapter(VehicleSupplyPort):

    def __init__(self, session: AsyncSession, graph_port: GraphPort):
        self._session = session
        self._graph = graph_port

    async def seed_vehicles(self) -> None:
        """Seeds scooters and carpool drivers into the database."""

        # Check if already seeded
        result = await self._session.execute(
            select(VehicleRow).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            print("[SUPPLY] Vehicles already seeded. Skipping.")
            return

        G = self._graph.get_graph()
        nodes = list(G.nodes())

        # Seed scooters at random nodes
        scooter_nodes = random.sample(
            nodes, min(config.NUM_SCOOTERS, len(nodes))
        )
        for i, node_id in enumerate(scooter_nodes):
            coords = self._graph.get_node_coords(node_id)
            row = VehicleRow(
                id=f"s_{i:03d}",
                type=VehicleType.SCOOTER.value,
                lat=coords.lat,
                lon=coords.lon,
                graph_node_id=node_id,
                is_available=True,
                battery_level=random.randint(40, 100),
                status=VehicleStatus.AVAILABLE.value,
            )
            self._session.add(row)

        # Seed carpool drivers with planned routes
        for i in range(config.NUM_CARPOOL_DRIVERS):
            home, work = random.sample(nodes, 2)

            try:
                route = nx.shortest_path(G, home, work, weight="distance")
            except nx.NetworkXNoPath:
                route = [home]

            home_coords = self._graph.get_node_coords(home)

            vehicle_classes = [
                ("gasoline", config.EMISSION_GASOLINE_CAR_G_KM),
                ("electric", config.EMISSION_ELECTRIC_CAR_G_KM),
            ]
            vc = random.choices(
                vehicle_classes, weights=[0.7, 0.3], k=1
            )[0]

            row = VehicleRow(
                id=f"c_{i:03d}",
                type=VehicleType.CARPOOL_DRIVER.value,
                lat=home_coords.lat,
                lon=home_coords.lon,
                graph_node_id=home,
                is_available=True,
                capacity=random.choice([1, 2, 3]),
                vehicle_class=vc[0],
                cost_per_km=config.CAR_COST_RUB_KM,
                emission_rate=vc[1],
                planned_route=route,
                status=VehicleStatus.AVAILABLE.value,
            )
            self._session.add(row)

        await self._session.commit()
        print(
            f"[SUPPLY] Seeded {config.NUM_SCOOTERS} scooters "
            f"and {config.NUM_CARPOOL_DRIVERS} drivers."
        )

    async def get_available_scooters(self) -> List[Scooter]:
        stmt = select(VehicleRow).where(
            VehicleRow.type == VehicleType.SCOOTER.value,
            VehicleRow.is_available == True,
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            Scooter(
                id=r.id,
                type=VehicleType.SCOOTER,
                location=GeoPoint(lat=r.lat, lon=r.lon),
                graph_node_id=r.graph_node_id,
                is_available=True,
                battery_level=r.battery_level or 100,
            )
            for r in rows
        ]

    async def get_available_drivers(
        self,
        origin_node: Optional[int] = None,
        dest_node: Optional[int] = None,
    ) -> List[CarpoolDriver]:
        stmt = select(VehicleRow).where(
            VehicleRow.type == VehicleType.CARPOOL_DRIVER.value,
            VehicleRow.is_available == True,
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        drivers = []
        for r in rows:
            drivers.append(
                CarpoolDriver(
                    id=r.id,
                    type=VehicleType.CARPOOL_DRIVER,
                    location=GeoPoint(lat=r.lat, lon=r.lon),
                    graph_node_id=r.graph_node_id,
                    is_available=True,
                    capacity=r.capacity or config.DEFAULT_CARPOOL_CAPACITY,
                    cost_per_km=r.cost_per_km or config.CAR_COST_RUB_KM,
                    emission_rate_g_km=r.emission_rate
                    or config.EMISSION_GASOLINE_CAR_G_KM,
                    vehicle_class=r.vehicle_class or "gasoline",
                    planned_route=r.planned_route,
                )
            )

        return drivers

    async def get_all_vehicles(self) -> List[Vehicle]:
        stmt = select(VehicleRow)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        vehicles = []
        for r in rows:
            v = Vehicle(
                id=r.id,
                type=VehicleType(r.type),
                location=GeoPoint(lat=r.lat, lon=r.lon),
                graph_node_id=r.graph_node_id,
                is_available=r.is_available,
            )
            vehicles.append(v)
        return vehicles

    async def update_vehicle_status(
        self, vehicle_id: str, is_available: bool
    ) -> None:
        stmt = (
            update(VehicleRow)
            .where(VehicleRow.id == vehicle_id)
            .values(is_available=is_available)
        )
        await self._session.execute(stmt)
        await self._session.commit()
