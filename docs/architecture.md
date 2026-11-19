# Architecture

## Overview

Three services, one database, one real-time layer.

```
                     ┌─────────────────────┐
                     │  Next.js dashboard  │
                     │  (restaurant/charity)│
                     └──────────┬──────────┘
                                │ REST + WebSocket
┌──────────────┐    ┌───────────┴──────────┐    ┌──────────────────┐
│ React Native │    │  API (TS + Fastify)  │    │ Matching engine  │
│ driver app + │◄──►│  PostgreSQL+PostGIS  │◄──►│ (Python, OR-Tools)│
│ consumer app │    │  Redis (pub-sub)     │    │ stateless workers │
└──────────────┘    └───────────┬──────────┘    └──────────────────┘
                                │
                     ┌──────────┴──────────┐
                     │ Toast/Clover webhook│
                     │ Google Maps Matrix  │
                     │ Twilio SMS          │
                     └─────────────────────┘
```

## Route optimization (the 10:45pm problem)

12 orders popping off at 10:45pm across town is a vehicle routing problem with hard time windows. We optimize for **maximum successful pickups before expiry**, not shortest distance — a missed pickup is food in the trash.

1. **Cluster first**: orders cluster by zone (geohash, ~2–3km cells). 12 orders across town usually collapse into 3–4 clusters.
2. **One driver per cluster**: the pickup sequence inside a cluster is a small TSP, solved with OR-Tools in milliseconds.
3. **Assignment is the hard part**: the solver scores orders by value × urgency and drops the ones that can't be reached in time, instead of building a route that fails halfway.
4. **Real travel times**: Google Maps Distance Matrix, not straight-line. At 10:45pm traffic is thin, so ETAs are reliable.
5. **Rolling re-optimization**: every new order triggers a re-solve, but assignments for drivers already en route stay frozen — nobody gets rerouted mid-drive.
6. **Driver supply**: the real constraint at 10:45pm is driver availability, so the system pre-positions drivers near high-surplus zones before close, based on the prediction model.

## State for active runs

Every order is a state machine in PostgreSQL:

```
pending → matched → assigned → picked_up → delivered
```

- Transitions go through a single function with **row-level locking**, so two drivers can never claim the same order.
- Redis holds the hot copy for reads (driver app polls it); PostgreSQL is the source of truth. If Redis dies, rebuild from PostgreSQL.
- If a driver goes offline mid-run, the assignment times out after 5 minutes and the order returns to `pending` for re-matching.

## Services

| Service | Language | Responsibility |
|---|---|---|
| API | TypeScript + Fastify | REST, WebSockets, webhooks, auth |
| Matching engine | Python + OR-Tools | Clustering, VRP solve, assignment |
| Dashboard | Next.js | Restaurant + charity web UI |
| Driver / consumer apps | React Native | Pickup flow, flash-sale browsing |

## Data

- **PostgreSQL + PostGIS**: orders, drivers, restaurants, deliveries, history. Geospatial queries are native.
- **Redis**: driver locations (geo sets), active assignments, pub-sub for order events.
