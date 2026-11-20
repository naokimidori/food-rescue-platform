"""Matching engine: cluster surplus orders, assign drivers, solve routes.

The 10:45pm problem: 12 orders pop off across town at close. This is a
vehicle routing problem with hard time windows. We optimize for maximum
successful pickups before expiry, not shortest distance -- a missed pickup
is food in the trash.

Pipeline:
  1. Cluster orders by geohash cell (~5km). 12 orders across town usually
     collapse into 3-4 clusters.
  2. Assign each cluster to the nearest available driver.
  3. Within a cluster, solve a TSP with time windows via OR-Tools. Orders
     that cannot be reached before expiry are dropped (penalty), instead
     of building a route that fails halfway.
  4. Re-solve on a rolling horizon: new orders trigger a re-run, but
     drivers already en route keep their frozen assignments.

Distances here are haversine (straight-line). Production swaps in the
Google Maps Distance Matrix for real travel times; the solver interface
is identical.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from geohash import cell_key

EARTH_RADIUS_KM = 6371.0
AVG_SPEED_KMH = 30.0  # city driving at night; production uses live ETAs


@dataclass
class Order:
    id: str
    lat: float
    lng: float
    value: float          # meal value in dollars (prize for collecting it)
    expires_in_min: int   # minutes until the food must be picked up
    weight_kg: float = 1.0


@dataclass
class Driver:
    id: str
    lat: float
    lng: float
    capacity_kg: float = 50.0


@dataclass
class Assignment:
    driver_id: str
    order_ids: list[str]          # pickup sequence
    dropped_ids: list[str]        # could not be reached in time
    total_value: float
    route_minutes: float


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def travel_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return haversine_km(lat1, lng1, lat2, lng2) / AVG_SPEED_KMH * 60


def cluster_orders(orders: list[Order], precision: int = 5) -> dict[str, list[Order]]:
    """Group orders into geohash cells. Returns {cell_key: [orders]}."""
    clusters: dict[str, list[Order]] = {}
    for order in orders:
        key = cell_key(order.lat, order.lng, precision)
        clusters.setdefault(key, []).append(order)
    return clusters


def _solve_cluster(driver: Driver, orders: list[Order]) -> Assignment:
    """Solve one cluster: one driver, N orders, TSP with time windows.

    Node 0 is the depot (driver start). Every order node carries a
    penalty equal to its value, so the solver drops orders it cannot
    reach in time instead of failing the whole route.
    """
    locations = [(driver.lat, driver.lng)] + [(o.lat, o.lng) for o in orders]
    n = len(locations)

    # Time matrix in minutes, rounded to ints for OR-Tools.
    time_matrix = [
        [int(round(travel_minutes(*locations[i], *locations[j])))
         for j in range(n)]
        for i in range(n)
    ]

    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index: int, to_index: int) -> int:
        return time_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)

    # Time dimension: each order must be visited before its expiry.
    # The depot (driver) has no deadline; orders get theirs.
    routing.AddDimensionWithVehicleTransits(
        [transit], 0, 24 * 60, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for node_idx, order in enumerate(orders, start=1):
        index = manager.NodeToIndex(node_idx)
        time_dim.CumulVar(index).SetRange(0, order.expires_in_min)
        # Dropping an order costs its value (in minutes-equivalent penalty
        # scaled up so value dominates pure travel time).
        penalty = int(order.value * 100)
        routing.AddDisjunction([index], penalty)

    search = pywrapcp.DefaultRoutingSearchParameters()
    search.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search.time_limit.FromSeconds(5)

    solution = routing.SolveWithParameters(search)
    picked: list[str] = []
    route_minutes = 0.0
    if solution:
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:
                picked.append(orders[node - 1].id)
            nxt = solution.Value(routing.NextVar(index))
            route_minutes += time_matrix[node][manager.IndexToNode(nxt)]
            index = nxt
    picked_set = set(picked)
    dropped = [o.id for o in orders if o.id not in picked_set]
    total_value = sum(o.value for o in orders if o.id in picked_set)
    return Assignment(
        driver_id=driver.id,
        order_ids=picked,
        dropped_ids=dropped,
        total_value=total_value,
        route_minutes=route_minutes,
    )


def match(orders: list[Order], drivers: list[Driver],
          precision: int = 5) -> list[Assignment]:
    """Full matching pass: cluster, assign nearest driver, solve each."""
    if not orders or not drivers:
        return []
    clusters = cluster_orders(orders, precision)
    # Cluster centroid -> nearest free driver (greedy, one driver per cluster).
    assignments: list[Assignment] = []
    used_drivers: set[str] = set()
    for _cell, cluster in clusters.items():
        clat = sum(o.lat for o in cluster) / len(cluster)
        clng = sum(o.lng for o in cluster) / len(cluster)
        free = [d for d in drivers if d.id not in used_drivers]
        if not free:
            break
        driver = min(free, key=lambda d: haversine_km(clat, clng, d.lat, d.lng))
        used_drivers.add(driver.id)
        assignments.append(_solve_cluster(driver, cluster))
    return assignments
