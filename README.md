# Food Rescue Platform

A global platform that rescues surplus food before it hits the dumpster and gets it to people who need it — fast.

## The problem

Roughly one third of all food produced — about 1.3 billion tons a year — is wasted, while hundreds of millions of people go hungry. The food exists. The people exist. The gap is logistics and timing: a restaurant manager has four minutes between rushes, and opening an app to post leftovers is not going to happen.

## The idea

Make the restaurant do **nothing**. The platform plugs into their POS, surplus auto-lists at close, and a driver is already on the way to pick it up. The restaurant gets paid for food it would have trashed, with zero extra effort.

## Modules

1. **Real-time surplus feed** — POS integrations (Toast, Clover) auto-list items flagged for disposal at close. No manual posting.
2. **AI matching engine** — predicts surplus before close, matches it in real time to the nearest charity or buyer.
3. **Logistics layer** — volunteer/pro driver routing, pickup windows, real-time tracking.
4. **Consumer app** — flash-sale style surplus food for people nearby, at a discount.
5. **Impact dashboard** — meals rescued, CO2 saved, money recovered, per restaurant and globally.

## Tech stack

- **API**: TypeScript + Fastify
- **Database**: PostgreSQL with PostGIS (orders, drivers, restaurants — all geospatial, one database)
- **Real-time**: Redis — driver locations, active assignments, pub-sub for order events
- **Matching engine**: separate Python service (OR-Tools). Pulls open orders + free drivers from Redis, runs clustering + VRP, writes assignments back to Redis and PostgreSQL in one transaction. Stateless, scales horizontally.
- **Frontend**: Next.js (restaurant/charity dashboard), React Native (driver + consumer apps). WebSockets for live updates.
- **Integrations**: Toast + Clover webhooks, Google Maps Distance Matrix for ETAs, Twilio for driver SMS.

See [docs/architecture.md](docs/architecture.md) for the full breakdown.

## Status

Early build. The matching engine + API is the first milestone, built with Devin.
