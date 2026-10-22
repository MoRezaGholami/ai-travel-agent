---
name: destination-guide
description: Recommend attractions, neighborhoods, transport, and local tips via search_knowledge (RAG).
---

# Skill: destination-guide

## Owner
`destination-agent` subagent only.

## When to use
- Task asks about attractions, neighborhoods, transport, etiquette, or destination tips.

## Required inputs
- Topic / query
- `city` when known (folder or alias): istanbul, dubai, tbilisi, berlin, barcelona, vienna, amsterdam, …

## Steps
1. Identify topic and city.
2. Call `search_knowledge(query, city, top_k=4)`.
3. Answer from retrieved chunks and mention source (source/heading).
4. Do not invent live flight/hotel prices — that is not this agent's job.

## Tools
- `search_knowledge`

## Errors
- If weak results, simplify the query (e.g. "attractions", "transport").
- If the city is not in the knowledge folders, say so honestly and suggest a supported city.
