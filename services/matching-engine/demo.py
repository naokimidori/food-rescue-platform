"""Demo: the 10:45pm problem — 12 surplus orders across town, 2 drivers.

Run from this directory:
    python demo.py

Expected: orders collapse into a few geohash clusters, each cluster goes
to its nearest driver, and the solver picks up everything it can reach
before expiry instead of failing the whole route.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from geohash import encode
from matcher import Driver, Order, cluster_orders, match

# Sanity check: classic geohash test vector.
assert encode(57.64911, 10.40744, 5) == "u4pru", encode(57.64911, 10.40744, 5)


def build_orders() -> list[Order]:
    # 12 orders around downtown San Francisco at 22:45, expiring in
    # 20-50 minutes. Values are the meal price in dollars.
    spots = [
        ("o01", 37.7749, -122.4194, 18.0, 45),
        ("o02", 37.7755, -122.4180, 12.0, 40),
        ("o03", 37.7762, -122.4201, 25.0, 30),
        ("o04", 37.7738, -122.4172, 9.0, 50),
        ("o05", 37.7849, -122.4094, 22.0, 35),
        ("o06", 37.7855, -122.4080, 15.0, 25),
        ("o07", 37.7838, -122.4102, 30.0, 20),
        ("o08", 37.7599, -122.4148, 11.0, 45),
        ("o09", 37.7605, -122.4135, 20.0, 30),
        ("o10", 37.7590, -122.4160, 8.0, 50),
        ("o11", 37.7949, -122.3994, 28.0, 40),
        ("o12", 37.7955, -122.3980, 14.0, 25),
    ]
    return [Order(id=i, lat=la, lng=ln, value=v, expires_in_min=e)
            for i, la, ln, v, e in spots]


def main() -> None:
    orders = build_orders()
    drivers = [
        Driver(id="d1", lat=37.7740, lng=-122.4190),
        Driver(id="d2", lat=37.7840, lng=-122.4090),
        Driver(id="d3", lat=37.7600, lng=-122.4150),
    ]

    clusters = cluster_orders(orders)
    print(f"orders: {len(orders)} -> {len(clusters)} clusters "
          f"({', '.join(f'{k}:{len(v)}' for k, v in clusters.items())})")

    assignments = match(orders, drivers)
    total_value = 0.0
    for a in assignments:
        total_value += a.total_value
        print(f"driver {a.driver_id}: pickup {a.order_ids} "
              f"dropped {a.dropped_ids} value ${a.total_value:.0f} "
              f"route {a.route_minutes:.1f} min")
    print(f"total rescued value: ${total_value:.0f} "
          f"of ${sum(o.value for o in orders):.0f}")


if __name__ == "__main__":
    main()
