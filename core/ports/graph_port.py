from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

import networkx as nx

from domain.value_objects import GeoPoint


class GraphPort(ABC):

    @abstractmethod
    def get_graph(self) -> nx.DiGraph:
        """Returns the full simplified Innopolis road graph."""
        ...

    @abstractmethod
    def get_nearest_node(self, lat: float, lon: float) -> int:
        """Returns the OSMnx node ID closest to the GPS coordinate."""
        ...

    @abstractmethod
    def get_node_coords(self, node_id: int) -> GeoPoint:
        """Converts a graph node ID to GPS coordinates."""
        ...

    @abstractmethod
    def get_edge_geometry(self, u: int, v: int) -> List[Tuple[float, float]]:
        """Returns the polyline GPS points for drawing edge (u, v) on a map."""
        ...

    @abstractmethod
    def get_all_nodes(self) -> List[int]:
        ...

    @abstractmethod
    def get_all_edges(self) -> List[Tuple[int, int, Dict[str, Any]]]:
        """Each edge dict must include 'distance' in km."""
        ...
