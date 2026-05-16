"""
Customer Research skill — enriches a guest profile with publicly available
social and interest data. Uses Exa when EXA_API_KEY is set, otherwise returns
rich mock data so the demo works out of the box.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Optional

# Tool schema for the Aura agent
TOOL_SCHEMA = {
    "type": "custom",
    "name": "research_guest",
    "description": (
        "Look up publicly available information about a guest to personalize their stay. "
        "Returns interests, food preferences, hobbies, and background context. "
        "Call this when you have a guest's name or email and want to tailor your service."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Guest's full name"},
            "email": {"type": "string", "description": "Guest's email address (optional but improves accuracy)"},
            "social_handles": {
                "type": "object",
                "description": "Known social handles, e.g. {\"twitter\": \"@handle\", \"instagram\": \"@handle\"}",
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["name"],
    },
}


@dataclass
class ResearchResult:
    name: str
    summary: str
    food_preferences: list[str] = field(default_factory=list)
    dietary_restrictions: list[str] = field(default_factory=list)
    hobbies: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    travel_style: str = ""
    notable_facts: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def research_guest(
    name: str,
    email: Optional[str] = None,
    social_handles: Optional[dict] = None,
) -> dict:
    """Entry point called by the agent tool dispatcher."""
    api_key = os.environ.get("EXA_API_KEY")
    if api_key:
        result = _exa_research(name, email, social_handles, api_key)
    else:
        result = _mock_research(name, email)
    return asdict(result)


# ---------------------------------------------------------------------------
# Exa-backed implementation
# ---------------------------------------------------------------------------

def _exa_research(
    name: str,
    email: Optional[str],
    social_handles: Optional[dict],
    api_key: str,
) -> ResearchResult:
    try:
        from exa_py import Exa  # type: ignore
    except ImportError:
        return _mock_research(name, email)

    exa = Exa(api_key=api_key)

    queries = [
        f'"{name}" interests hobbies food',
        f'"{name}" site:linkedin.com',
        f'"{name}" site:twitter.com OR site:x.com',
    ]
    if email:
        domain = email.split("@")[-1]
        if domain not in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com"):
            queries.append(f'"{name}" site:{domain}')

    raw_texts: list[str] = []
    sources: list[str] = []

    for query in queries:
        try:
            resp = exa.search(query, num_results=3)
            for r in resp.results:
                if r.text:
                    raw_texts.append(r.text[:800])
                if r.url:
                    sources.append(r.url)
        except Exception:
            continue

    if not raw_texts:
        return _mock_research(name, email)

    combined = "\n\n---\n\n".join(raw_texts[:6])
    return _extract_with_claude(name, combined, sources)


def _extract_with_claude(name: str, raw_text: str, sources: list[str]) -> ResearchResult:
    """Use Claude to parse free-form web snippets into a structured profile."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = f"""You are a luxury hotel concierge assistant. Based on the web research excerpts below about "{name}", extract a guest preference profile.

Web excerpts:
{raw_text}

Return ONLY valid JSON with this exact shape:
{{
  "summary": "2-3 sentence bio relevant to hospitality",
  "food_preferences": ["list", "of", "food interests or cuisine preferences"],
  "dietary_restrictions": ["any dietary restrictions or empty list"],
  "hobbies": ["list", "of", "hobbies"],
  "interests": ["list", "of", "topics or passions"],
  "travel_style": "one phrase describing travel style, e.g. 'adventure seeker' or 'wellness-focused luxury traveler'",
  "notable_facts": ["any facts useful for personalizing a hotel stay"]
}}

If information is unknown, use an empty list or empty string. Never invent facts."""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        raw = msg.content[0].text.strip()
        # strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
    except (json.JSONDecodeError, IndexError, KeyError):
        return _mock_research(name, None)

    return ResearchResult(
        name=name,
        summary=data.get("summary", ""),
        food_preferences=data.get("food_preferences", []),
        dietary_restrictions=data.get("dietary_restrictions", []),
        hobbies=data.get("hobbies", []),
        interests=data.get("interests", []),
        travel_style=data.get("travel_style", ""),
        notable_facts=data.get("notable_facts", []),
        sources=sources[:5],
    )


# ---------------------------------------------------------------------------
# Mock fallback (used when EXA_API_KEY is absent)
# ---------------------------------------------------------------------------

_MOCK_PROFILES: dict[str, ResearchResult] = {
    "kelvin ma": ResearchResult(
        name="Kelvin Ma",
        summary=(
            "Kelvin Ma is a tech entrepreneur based in San Francisco with a strong interest "
            "in AI and startups. He enjoys exploring diverse culinary scenes and is known for "
            "an active lifestyle balancing work and outdoor pursuits."
        ),
        food_preferences=["Japanese", "Korean BBQ", "farm-to-table", "specialty coffee", "omakase"],
        dietary_restrictions=[],
        hobbies=["hiking", "tennis", "photography", "reading"],
        interests=["artificial intelligence", "startups", "design", "travel"],
        travel_style="experience-driven luxury traveler",
        notable_facts=[
            "Frequent visitor to SF Bay Area fine dining",
            "Enjoys late-night room service after long work sessions",
            "Prefers a quiet, cool room for deep focus and sleep",
        ],
        sources=[],
    ),
}

_DEFAULT_MOCK = ResearchResult(
    name="",
    summary="Valued guest with a discerning taste for quality and personalized service.",
    food_preferences=["local cuisine", "fresh seafood", "artisan breads"],
    dietary_restrictions=[],
    hobbies=["travel", "reading", "wellness"],
    interests=["culture", "gastronomy", "design"],
    travel_style="luxury leisure traveler",
    notable_facts=[],
    sources=[],
)


def _mock_research(name: str, email: Optional[str]) -> ResearchResult:
    key = name.lower().strip()
    profile = _MOCK_PROFILES.get(key, _DEFAULT_MOCK)
    profile.name = name  # ensure name is set correctly
    return profile
