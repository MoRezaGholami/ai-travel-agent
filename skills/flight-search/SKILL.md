---
name: flight-search
description: Collect flight parameters, search with search_flights, and compare options by price and schedule.
---

# Skill: flight-search

## When to use
- User wants flights (search, cheaper options, date/route change).
- Part of trip planning that needs a flight.

## Required inputs
- `origin` (e.g. Tehran)
- `destination` (e.g. Istanbul)
- `departure_date` optional (YYYY-MM-DD)
- `max_price` optional

If origin or destination is missing, ask. If date is missing, search without it or ask one short question.

## Steps
1. Extract parameters from the user message.
2. Ask one short follow-up if something critical is missing.
3. Call `search_flights`.
4. Summarize 2–4 best options (id, airline, time, price, seats).
5. If user asks for cheaper options, search again with `max_price` or filter the list.

## Tools
- `search_flights`

## Errors
- If empty results, suggest alternate date/route and search again.
- Use flight ids only from tool output; never invent them.
