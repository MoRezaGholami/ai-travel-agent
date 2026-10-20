---
name: trip-planning
description: Combine flight, hotel, and destination info into a simple multi-step trip plan.
---

# Skill: trip-planning

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
2. Search flights using flight-search guidance.
3. Search hotels using hotel-search guidance (hotel dates aligned with the trip).
4. Optionally pull 2–3 attractions via destination-guide.
5. Return one summary: recommended flight + hotel + attractions.
6. Ask whether to book; do not book without confirmation.

## Tools
- `search_flights`
- `search_hotels`
- `search_knowledge`

## Errors
- If one search is empty, retry that part with alternate params; don't abandon the whole plan.
