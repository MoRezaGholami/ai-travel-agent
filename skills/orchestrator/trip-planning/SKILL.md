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
4. **RAG path (decision):** if the user wants attractions / neighborhoods / tips,
   delegate to `destination-agent` (it calls `search_knowledge` → BM25).
5. **RAG path (decision):** if they want a day-by-day plan, delegate to
   `itinerary-agent` (also `search_knowledge`, multiple focused queries).
6. Return one summary: flight + hotel + attractions/itinerary.
7. If user wants to book, confirm details, then delegate to `booking-agent`.

## RAG vs live data
- RAG = static city knowledge under `rag/knowledge/**` via MCP `search_knowledge`.
- Live inventory = `search_flights` / `search_hotels` / booking tools.
- Never mix: do not invent attractions from flight results, or prices from RAG chunks.

## Subagents
- `flight-agent`
- `hotel-agent`
- `destination-agent` (RAG)
- `itinerary-agent` (RAG)
- `booking-agent`

## Errors
- If one specialist returns empty results, retry that part with alternate params; don't abandon the whole plan.
