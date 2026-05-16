---
name: guest-research
description: >
  Research a hotel guest using public web sources to uncover interests, food preferences,
  hobbies, and travel style — enabling hyper-personalized service. Use this skill whenever
  Aura receives a new guest contact, a guest checks in, or you want to personalize a room
  prep, amenity selection, or dining recommendation.
compatibility: Requires Python 3.9+, uv, and EXA_API_KEY + ANTHROPIC_API_KEY in the environment.
metadata:
  author: rosewood-aura
  version: "1.0"
---

## Overview

This skill searches public web sources (personal sites, LinkedIn, GitHub, social profiles)
for a named guest, then uses Claude to distill the raw results into a structured preference
profile. If `EXA_API_KEY` is not set, it falls back to rich mock data so the demo always works.

## When to activate

- A guest emails, texts, or calls for the first time in a stay
- Aura is about to call `update_pms_room_prep` and wants to choose a personalized amenity
- A guest asks for a dining or activity recommendation
- Any time you want to address a guest by name with genuine context ("Of course, Mr. Ma — given your love of omakase…")

## Inputs

| Field            | Required | Description                                              |
|------------------|----------|----------------------------------------------------------|
| `name`           | Yes      | Guest's full name                                        |
| `email`          | No       | Improves accuracy; non-generic domains add a domain search |
| `social_handles` | No       | Dict of `{"twitter": "@handle", "instagram": "@handle"}` |

## Outputs

The script prints a JSON object:

```json
{
  "name": "Kelvin Ma",
  "summary": "...",
  "food_preferences": ["Japanese", "omakase", "specialty coffee"],
  "dietary_restrictions": [],
  "hobbies": ["hiking", "photography", "cooking", "music"],
  "interests": ["machine learning", "AI", "startups"],
  "travel_style": "active and intellectually-driven luxury traveler",
  "notable_facts": ["Prefers quiet rooms", "Enjoys late-night room service"],
  "sources": ["https://kelvin.ma/", "..."]
}
```

## How to use

### Run as a script

```bash
uv run skills/guest-research/scripts/research.py \
  --name "Kelvin Ma" \
  --email "kelvin.ma23@gmail.com"
```

With social handles:

```bash
uv run skills/guest-research/scripts/research.py \
  --name "Kelvin Ma" \
  --email "kelvin.ma23@gmail.com" \
  --twitter "@KelvinHMa"
```

### Call as a Python function (server integration)

```python
from skills.customer_research import research_guest

profile = research_guest("Kelvin Ma", email="kelvin.ma23@gmail.com")
# profile is a dict with the fields above
```

The `research_guest` function is also registered as the `research_guest` tool in
`server/tools.py`, so Aura can call it directly during an agent session.

## Steps

1. Build search queries: `"{name}" interests hobbies food`, `"{name}" site:linkedin.com`,
   `"{name}" site:twitter.com OR site:x.com`. If email has a non-generic domain, also query
   `"{name}" site:{domain}`.
2. Run each query through Exa (`search()`), collect URLs + text (up to 800 chars each).
3. Pass all snippets to Claude Haiku with a structured extraction prompt. Strip any markdown
   code fences from the response before parsing JSON.
4. Return the `ResearchResult` dataclass (serialised to dict).
5. If Exa returns no results, or `EXA_API_KEY` is absent, return the mock profile for
   "Kelvin Ma" or the generic default for unknown guests.

## How to use the result in Aura

After calling `research_guest`, weave the profile into the guest's context and use it to:

- Choose a welcome amenity (`food_preferences` → match to menu items)
- Set room temperature based on `notable_facts`
- Open the conversation with a personalized line referencing a known hobby or interest
- Suggest spa treatments, restaurants, or activities aligned with `travel_style`

## Edge cases

- **Name collision**: "Kelvin Ma" matches multiple people on LinkedIn. When a personal
  website URL is known, pass it as a social handle to anchor the search.
- **No results**: Falls back to mock data silently. Aura should still greet the guest warmly
  using standard information from the PMS.
- **Rate limits**: Exa queries run sequentially; each failed query is skipped with `continue`.
