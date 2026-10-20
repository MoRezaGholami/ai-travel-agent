---
name: trip-planning
description: Combine flight, hotel, and destination info into a simple multi-step trip plan by delegating to specialist subagents.
---

# Skill: trip-planning

## Owner
Orchestrator only (not flight/hotel/destination subagents).

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
2. Delegate flight search to `flight-agent`.
3. Delegate hotel search to `hotel-agent` (dates aligned with the trip).
4. Optionally ask `destination-agent` for 2–3 attractions.
5. Return one summary: recommended flight + hotel + attractions.
6. Ask whether to book; do not book without confirmation.

## Subagents
- `flight-agent`
- `hotel-agent`
- `destination-agent`

## Errors
- If one specialist returns empty results, retry that part with alternate params; don't abandon the whole plan.
