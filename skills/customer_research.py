"""
customer_research.py — Guest research module for Rosewood Aura.
Uses Exa for web search + Claude to distill results into a structured profile.
Falls back to mock data if API keys are absent.
"""
import json
import os
import re
import sys

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")

TOOL_SCHEMA = {
    "name": "research_guest",
    "description": "Research a hotel guest using public web sources.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
            "social_handles": {"type": "object"},
        },
        "required": ["name"],
    },
}

MOCK_PROFILE = {
    "name": "Guest",
    "summary": "No public information found. Standard luxury hospitality protocol applies.",
    "food_preferences": [],
    "dietary_restrictions": [],
    "hobbies": [],
    "interests": [],
    "travel_style": "unknown",
    "notable_facts": [],
    "sources": [],
}


def _exa_search(query: str, num_results: int = 3) -> list[dict]:
    import urllib.request, urllib.parse
    try:
        data = json.dumps({
            "query": query,
            "numResults": num_results,
            "useAutoprompt": True,
            "type": "neural",
            "contents": {"text": {"maxCharacters": 800}},
        }).encode()
        req = urllib.request.Request(
            "https://api.exa.ai/search",
            data=data,
            headers={"Content-Type": "application/json", "x-api-key": EXA_API_KEY},
        )
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read()).get("results", [])
    except Exception as e:
        print(f"[Exa error: {e}]", file=sys.stderr)
        return []


def _claude_extract(name: str, snippets: list[str]) -> dict:
    import urllib.request
    try:
        context = "\n\n".join(snippets[:8])
        prompt = f"""You are a luxury hotel concierge AI. Based on the following web search snippets about "{name}", 
extract a structured guest profile. Return ONLY valid JSON with these exact fields:
{{
  "name": "{name}",
  "summary": "2-3 sentence summary",
  "food_preferences": ["list", "of", "foods"],
  "dietary_restrictions": [],
  "hobbies": ["list"],
  "interests": ["list"],
  "travel_style": "one phrase",
  "notable_facts": ["list of useful concierge intel"],
  "sources": []
}}

Web snippets:
{context}

If no useful info found, return the JSON with empty arrays and "No public information found" as summary."""

        data = json.dumps({
            "model": "claude-haiku-4-5",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
        )
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        text = result["content"][0]["text"]
        # Strip markdown fences if present
        text = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
        return json.loads(text)
    except Exception as e:
        print(f"[Claude error: {e}]", file=sys.stderr)
        return None


def research_guest(name: str, email: str = None, social_handles: dict = None) -> dict:
    if not EXA_API_KEY:
        profile = dict(MOCK_PROFILE)
        profile["name"] = name
        return profile

    queries = [
        f'"{name}" interests hobbies food preferences',
        f'"{name}" site:linkedin.com',
        f'"{name}" site:twitter.com OR site:x.com',
    ]

    # If email has a non-generic domain, search that domain too
    if email:
        domain = email.split("@")[-1]
        if domain not in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"):
            queries.append(f'"{name}" site:{domain}')

    if social_handles:
        for platform, handle in social_handles.items():
            queries.append(f'"{handle}" {platform}')

    snippets = []
    sources = []
    for q in queries:
        results = _exa_search(q, num_results=2)
        for r in results:
            text = r.get("text", "").strip()
            url = r.get("url", "")
            if text:
                snippets.append(f"[{url}]\n{text}")
            if url:
                sources.append(url)

    if not snippets:
        profile = dict(MOCK_PROFILE)
        profile["name"] = name
        return profile

    profile = _claude_extract(name, snippets)
    if not profile:
        profile = dict(MOCK_PROFILE)
        profile["name"] = name

    profile["sources"] = list(set(sources))[:5]
    return profile
