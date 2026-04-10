"""
Loads the real Innopolis street network using OSMnx.
Applies graph simplification per our design decision.
Graph is cached to disk so subsequent startups are instant.
Falls back across multiple Overpass API mirrors if the primary times out.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import networkx as nx
import osmnx as ox

import config
from core.ports.graph_port import GraphPort
from domain.value_objects import GeoPoint

# Cache file lives at the project root (next to main.py)
_CACHE_PATH = Path(__file__).parent.parent.parent / "innopolis_graph.graphml"

# Overpass API mirrors to try in order
_OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def _download_graph() -> nx.MultiDiGraph:
    """Try each Overpass mirror in turn with a generous timeout."""
    last_exc: Exception | None = None
    for endpoint in _OVERPASS_ENDPOINTS:
        try:
            print(f"[GEO] Trying Overpass endpoint: {endpoint}")
            ox.settings.overpass_url = endpoint
            ox.settings.timeout = 1800  # seconds
            G = ox.graph_from_point(
                center_point=(
                    config.INNOPOLIS_CENTER_LAT,
                    config.INNOPOLIS_CENTER_LON,
                ),
                dist=config.GRAPH_LOAD_RADIUS_M,
                network_type="drive",
                simplify=True,
            )
            return G
        except Exception as exc:
            print(f"[GEO] Endpoint {endpoint} failed: {exc!r}")
            last_exc = exc
    raise RuntimeError(
        "All Overpass API endpoints failed. Check your internet connection."
    ) from last_exc


class OsmnxGraphAdapter(GraphPort):

    def __init__(self):
        self._graph: nx.DiGraph | None = None

    def load(self) -> None:
        """
        Loads the Innopolis road network.
        On first run downloads from OpenStreetMap (tries multiple mirrors)
        and caches to disk as GraphML.
        Subsequent runs load from the local cache in < 1 second.
        """
        if _CACHE_PATH.exists():
            print(f"[GEO] Loading Innopolis graph from cache: {_CACHE_PATH}")
            G = ox.load_graphml(_CACHE_PATH)
        else:
            print("[GEO] Downloading Innopolis graph from OpenStreetMap...")
            G = _download_graph()
            # Ensure distances are in meters, then convert to km on edges
            G = ox.distance.add_edge_lengths(G)
            ox.save_graphml(G, _CACHE_PATH)
            print(f"[GEO] Graph cached to {_CACHE_PATH}")

        for u, v, data in G.edges(data=True):
            data["distance"] = data.get("length", 100.0) / 1000.0

        self._graph = G

        node_count = G.number_of_nodes()
        edge_count = G.number_of_edges()
        print(
            f"[GEO] Innopolis graph loaded: {node_count} nodes, "
            f"{edge_count} edges (simplified)."
        )

    def get_graph(self) -> nx.DiGraph:
        if self._graph is None:
            raise RuntimeError("Graph not loaded. Call load() first.")
        return self._graph

    def get_nearest_node(self, lat: float, lon: float) -> int:
        if self._graph is None:
            raise RuntimeError("Graph not loaded.")
        return ox.distance.nearest_nodes(self._graph, lon, lat)

    def get_node_coords(self, node_id: int) -> GeoPoint:
        if self._graph is None:
            raise RuntimeError("Graph not loaded.")
        node = self._graph.nodes[node_id]
        return GeoPoint(lat=node["y"], lon=node["x"])

    def get_edge_geometry(
        self, u: int, v: int
    ) -> List[Tuple[float, float]]:
        if self._graph is None:
            raise RuntimeError("Graph not loaded.")

        data = self._graph.get_edge_data(u, v)
        if data is None:
            # Try the first key for MultiDiGraph
            if isinstance(self._graph, nx.MultiDiGraph):
                keys = list(self._graph[u][v].keys())
                if keys:
                    data = self._graph[u][v][keys[0]]

        if data and "geometry" in data:
            coords = list(data["geometry"].coords)
            return [(lat, lon) for lon, lat in coords]

        # Fallback: straight line between nodes
        u_c = self.get_node_coords(u)
        v_c = self.get_node_coords(v)
        return [(u_c.lat, u_c.lon), (v_c.lat, v_c.lon)]

    def get_all_nodes(self) -> List[int]:
        return list(self.get_graph().nodes())

    def get_all_edges(self) -> List[Tuple[int, int, Dict[str, Any]]]:
        return list(self.get_graph().edges(data=True))
