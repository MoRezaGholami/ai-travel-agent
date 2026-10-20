---
name: hotel-search
description: Search and filter hotels by city, stay dates, rooms, price, and stars using search_hotels.
---

# Skill: hotel-search

## Owner
`hotel-agent` subagent only.

## When to use
- Task asks for hotels / lodging options.

## Required inputs
- `city` (e.g. Istanbul)
- `check_in` and `check_out` as YYYY-MM-DD (required by the tool)
- `rooms` default 1
- optional: `max_price_per_night`, `min_stars`

If stay dates are missing from the task, report what is needed.

## Steps
1. Extract parameters and normalize dates to YYYY-MM-DD.
2. Call `search_hotels`.
3. Summarize 2–4 options with name, stars, nightly price, and total_price.
4. If budget dropped, search again with `max_price_per_night`.

## Tools
- `search_hotels`

## Errors
- If not enough rooms, reduce rooms or suggest another hotel.
- If dates are invalid, say so clearly.
- Never create bookings.
