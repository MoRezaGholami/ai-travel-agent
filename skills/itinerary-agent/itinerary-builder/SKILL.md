---
name: itinerary-builder
description: Build a realistic day-by-day itinerary using search_knowledge for a destination.
---

# Skill: itinerary-builder

## Owner
`itinerary-agent` only.

## When to use
- User/orchestrator wants a multi-day plan (e.g. "3 days in Istanbul").

## Required inputs
- `city` (istanbul / dubai)
- number of days (default 3 if missing)
- optional interests (history, food, nightlife, budget)

## Steps
1. Query knowledge for attractions (and neighborhoods/transport if useful).
2. Cluster nearby sights per day to reduce travel time.
3. Produce Day 1..N with morning / afternoon / evening suggestions.
4. Add short transport tips when relevant.
5. Do not invent museum hours or live prices; stay grounded in retrieved text.

## Tools
- `search_knowledge` (call multiple times with focused queries)

## Errors
- If knowledge is thin, provide a shorter plan and say what is missing.
- Only Istanbul and Dubai are covered well today.
