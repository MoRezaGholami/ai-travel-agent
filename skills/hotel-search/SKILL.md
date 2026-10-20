---
name: hotel-search
description: Search and filter hotels by city, stay dates, rooms, price, and stars using search_hotels.
---

# Skill: hotel-search

## When to use
- User wants a hotel / stay.
- Part of trip planning that needs lodging.

## Required inputs
- `city` (e.g. Istanbul)
- `check_in` and `check_out` as YYYY-MM-DD (required by the tool)
- `rooms` default 1
- optional: `max_price_per_night`, `min_stars`

If stay dates are missing, ask (at least check-in and nights, or check-out).

## Steps
1. Extract parameters and normalize dates to YYYY-MM-DD.
2. Call `search_hotels`.
3. Summarize 2–4 options with name, stars, nightly price, and total_price.
4. If budget dropped, search again with `max_price_per_night`.

## Tools
- `search_hotels`

## Errors
- If not enough rooms, reduce rooms or suggest another hotel.
- If dates are invalid (checkout before checkin), ask to fix them.
