# Matching engine

Clusters surplus orders by geohash cell, assigns each cluster to its
nearest driver, then solves a TSP with time windows (OR-Tools) per
cluster. Orders that cannot be reached before expiry are dropped with
a penalty equal to their value — a missed pickup is food in the trash,
so the solver maximizes rescued value, not shortest distance.

## Run the demo

```bash
python -m venv .venv
.venv/bin/pip install ortools
.venv/bin/python demo.py
```

Demo scenario: 12 orders across downtown San Francisco at 22:45,
3 drivers. Expected output: orders collapse into a few clusters and
everything reachable before expiry gets picked up.

## Files

- `geohash.py` — pure-Python geohash encode, no dependencies.
- `matcher.py` — clustering, driver assignment, OR-Tools routing.
- `demo.py` — the 10:45pm scenario end to end.
