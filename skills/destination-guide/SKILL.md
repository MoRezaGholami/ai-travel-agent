---
name: destination-guide
description: Recommend attractions, neighborhoods, transport, and local tips via search_knowledge (RAG).
---

# Skill: destination-guide

## When to use
- User asks about attractions, where to stay areas, transport, etiquette, or destination tips.
- After destination is chosen, to enrich the trip plan.

## Required inputs
- Topic / query
- `city` when known: istanbul / dubai (or Persian equivalents)

## Steps
1. Identify topic and city.
2. Call `search_knowledge(query, city, top_k=4)`.
3. Answer from retrieved chunks and mention source (source/heading).
4. Do not invent live flight/hotel prices from RAG — use search_flights / search_hotels.

## Tools
- `search_knowledge`

## Errors
- If weak results, simplify the query (e.g. "attractions", "transport").
- Knowledge is currently filled for Istanbul and Dubai only; say so honestly for other cities.
