---
name: flight-search
description: Collect flight parameters, search with search_flights, and compare options by price and schedule.
---

# Skill: flight-search

## Owner
`flight-agent` subagent only.

## When to use
- Task asks for flights (search, cheaper options, date/route change).

## Required inputs
- `origin` (e.g. Tehran)
- `destination` (e.g. Istanbul)
- `departure_date` optional (YYYY-MM-DD)
- `max_price` optional

If origin or destination is missing from the task, report what is missing; do not invent values.

## Steps
1. Extract parameters from the task.
2. Call `search_flights`.
3. Summarize 2–4 best options (id, airline, time, price, seats).
4. If asked for cheaper options, search again with `max_price` or filter the list.

## Tools
- `search_flights`

## Errors
- If empty results, suggest alternate date/route and search again.
- Use flight ids only from tool output; never invent them.
- Never create bookings.
