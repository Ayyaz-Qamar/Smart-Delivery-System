"""
Route optimization.

Two implementations:
1. nearest_neighbor_route() — pure Python, no network. Fast, deterministic, ~10–25%
   above optimal. Used as the production default and as a fallback.
2. osrm_optimize_route() — calls a free public OSRM server for real road-network
   distances. Used when ROUTING_BACKEND=osrm in the .env.

Both return (ordered_indices, total_distance_km).
"""
import os
import requests
from typing import List, Tuple
from ml.rl_optimizer import haversine_km

OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
ROUTING_BACKEND = os.getenv("ROUTING_BACKEND", "nearest_neighbor")  # or "osrm" or "rl"


def nearest_neighbor_route(start: Tuple[float, float],
                           stops: List[Tuple[float, float]]) -> Tuple[List[int], float]:
    """Greedy nearest-neighbor TSP heuristic. Always available, no network needed."""
    if not stops:
        return [], 0.0

    remaining = list(range(len(stops)))
    order, total = [], 0.0
    current = start

    while remaining:
        # Pick the nearest unvisited stop
        nearest_idx = min(remaining, key=lambda i: haversine_km(*current, *stops[i]))
        total += haversine_km(*current, *stops[nearest_idx])
        order.append(nearest_idx)
        current = stops[nearest_idx]
        remaining.remove(nearest_idx)

    return order, total


def osrm_optimize_route(start: Tuple[float, float],
                        stops: List[Tuple[float, float]]) -> Tuple[List[int], float]:
    """
    Use OSRM's `trip` service to solve the TSP on the real road network.
    Falls back to nearest_neighbor if OSRM is unreachable.
    """
    coords = [start] + stops
    coord_str = ";".join(f"{lng},{lat}" for lat, lng in coords)  # OSRM uses lng,lat
    url = f"{OSRM_URL}/trip/v1/driving/{coord_str}?source=first&roundtrip=false"

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("code") != "Ok":
            raise RuntimeError(data.get("message", "OSRM error"))

        # OSRM returns waypoints with `waypoint_index` = order in the optimized trip
        waypoints = sorted(data["waypoints"], key=lambda w: w["waypoint_index"])
        # Skip the start (input index 0). Subtract 1 to map back to stops-index space.
        order = [w["trips_index"] for w in waypoints if w["trips_index"] != 0]
        # `trips_index` is per-trip; it's safer to use input order:
        order = [w["waypoint_index"] for w in data["waypoints"]][1:]  # drop start
        # Re-derive order: indices in the original `coords` array sorted by waypoint_index
        order_in_input = sorted(range(1, len(coords)),
                                key=lambda i: data["waypoints"][i]["waypoint_index"])
        order = [i - 1 for i in order_in_input]  # back to stops-index space

        total_meters = sum(t["distance"] for t in data["trips"])
        return order, total_meters / 1000.0
    except Exception as e:
        print(f"[OSRM] Falling back to nearest-neighbor: {e}")
        return nearest_neighbor_route(start, stops)


def optimize_route(start: Tuple[float, float],
                   stops: List[Tuple[float, float]],
                   use_rl: bool = False) -> Tuple[List[int], float]:
    """Top-level dispatcher. Chooses backend based on flag and env config."""
    if use_rl:
        from ml.rl_optimizer import rl_optimize_route
        return rl_optimize_route(start, stops)

    if ROUTING_BACKEND == "osrm":
        return osrm_optimize_route(start, stops)

    return nearest_neighbor_route(start, stops)
