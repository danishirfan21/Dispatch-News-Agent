import json
import logging

import httpx

from ..config import settings
from ..models import ParseInterestsResponse

logger = logging.getLogger("backboard")

SYSTEM_PROMPT = """You turn a short, casual description of someone's news interests into a \
structured interest profile for a personalized news app.

Rules:
- Interpret broad, natural-language interests the way a person means them.
- Identify anything the person explicitly says they do NOT want (exclusions).
- For each interest, infer a small set of reasonable search terms a news search \
engine could use to find relevant coverage.
- Preserve geographic specificity exactly as stated (e.g. "Pakistan's economy" is \
about Pakistan, not economics in general).
- Do not invent interests the person did not express, and do not add generic \
categories "for completeness".
- Keep interests reasonably broad — a handful of meaningful categories, not dozens \
of narrow ones. Group closely related mentions (e.g. "OpenAI" and "AI research") \
into one interest when that reflects what the person meant.
- Assign each interest a priority of "high", "medium", or "low" based on how much \
emphasis the person gave it.
- Output ONLY valid JSON matching this exact shape, with no commentary, no markdown \
fences, and no extra keys:

{
  "interests": [
    {"topic": "string", "priority": "high" | "medium" | "low", "search_terms": ["string"]}
  ],
  "excluded_topics": ["string"]
}
"""


class BackboardError(Exception):
    """Raised for any Backboard-related failure. Message is safe to show the user."""


async def parse_interests(text: str) -> ParseInterestsResponse:
    if not settings.backboard_api_key:
        logger.error("Backboard request skipped: API key is not configured")
        raise BackboardError("The AI service isn't configured on the server yet.")

    payload = {
        "content": text,
        "system_prompt": SYSTEM_PROMPT,
        "llm_provider": settings.backboard_llm_provider,
        "model_name": settings.backboard_model,
        "memory": "off",
        "web_search": "off",
        "json_output": True,
    }
    headers = {"X-API-Key": settings.backboard_api_key}

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{settings.backboard_base_url}/threads/messages",
                json=payload,
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        logger.error("Backboard request timed out: %s", type(exc).__name__)
        raise BackboardError("The AI service took too long to respond. Please try again.") from exc
    except httpx.RequestError as exc:
        logger.error("Backboard request failed: %s", type(exc).__name__)
        raise BackboardError("Couldn't reach the AI service. Please try again.") from exc

    if response.status_code != 200:
        logger.error("Backboard returned status %s", response.status_code)
        raise BackboardError("The AI service returned an error. Please try again.")

    try:
        body = response.json()
        content = body["content"]
        if content is None:
            raise KeyError("content")
    except (KeyError, ValueError) as exc:
        logger.error("Backboard response had unexpected shape: %s", type(exc).__name__)
        raise BackboardError("The AI service sent back something we couldn't read.") from exc

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.error("Backboard content was not valid JSON: %s", type(exc).__name__)
        raise BackboardError("The AI service sent back something we couldn't read.") from exc

    try:
        return ParseInterestsResponse.model_validate(parsed)
    except Exception as exc:
        logger.error("Backboard JSON did not match expected schema: %s", type(exc).__name__)
        raise BackboardError("The AI service sent back something we couldn't read.") from exc
