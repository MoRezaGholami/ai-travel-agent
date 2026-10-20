---
name: trip-planning
description: Combine specialist subagents into a simple multi-step trip plan.
---

# Skill: trip-planning

## Owner
Orchestrator only.

## When to use
- Combined requests like "Find a flight and hotel for Istanbul".
- User wants a multi-day trip outline.

## Required inputs
- Destination (and preferably origin)
- Trip window, or at least outbound date and number of nights
- Optional budget
- User name only when booking starts

## Steps
1. Fill missing params with minimal questions.
2. Delegate flights to `flight-agent`.
3. Delegate hotels to `hotel-agent` (dates aligned with the trip).
4. Optionally ask `destination-agent` for tips/attractions.
5. Optionally ask `itinerary-agent` for a day-by-day plan.
6. Return one summary: flight + hotel + attractions/itinerary.
7. If user wants to book, confirm details, then delegate to `booking-agent`.

## Subagents
- `flight-agent`
- `hotel-agent`
- `destination-agent`
- `itinerary-agent`
- `booking-agent`

## Errors
- If one specialist returns empty results, retry that part with alternate params; don't abandon the whole plan.
