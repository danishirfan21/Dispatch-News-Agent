import json
import logging

from pydantic import BaseModel, ValidationError

from ..models import Article
from .backboard import send_json_message

logger = logging.getLogger("watch_analysis")

SYSTEM_PROMPT = """You determine whether a specific real-world news story a user is tracking has \
meaningfully changed since the last time it was checked.

You will receive JSON with:
- "headline": the story's original headline
- "topic": its topic/category
- "known_state": a concise description of what is currently known about this story
- "watch_condition": an optional user-written condition describing specifically what they want \
to be told about (may be empty)
- "major_developments_only": whether the user wants to be notified only for major developments
- "last_checked_at": when this watch was last checked, or null if this is the first check
- "recent_developments": short summaries of developments already recorded for this watch, most \
recent first (may be empty)
- "articles": freshly retrieved news articles, each with "id", "title", "source", "url", \
"published_at", and sometimes "snippet"

Your job:
1. Decide whether the articles contain a genuinely new, material factual development compared to \
known_state — not merely another outlet repeating the same facts, a reworded headline, \
speculation, or commentary. A fact already represented in known_state OR in recent_developments is \
NOT a new material change merely because another publication reports it again.
2. If major_developments_only is true, apply a SIGNIFICANTLY higher bar: only count things like \
an official decision, a confirmed outcome, a signed agreement, a major escalation/de-escalation, \
a court ruling, a leadership change, a release/launch, or a comparably major policy change. Do \
NOT count minor incremental detail, analyst opinion, speculation, or another source simply \
confirming already-known facts.
3. If major_developments_only is false, a smaller but still genuinely new factual development may \
count — but never treat "another new article exists" by itself as a material change.
4. Separately, decide whether the user's watch_condition (if any) is now satisfied by the \
evidence. This is independent from material_change — a material change can happen while the \
specific condition is still not met, and a condition can be unmet even though something changed. \
If watch_condition is empty, condition_satisfied should be false.
5. Reason ONLY from the supplied article evidence. Never use prior knowledge, assumptions, or \
anything not present in the supplied titles/snippets to decide there was a change. If the \
evidence is thin, contradictory, or doesn't clearly establish a new fact, prefer \
material_change=false.
6. If material_change is true, write a concise new_known_state describing the current state of \
the story (grounded only in known_state plus the supporting evidence). If material_change is \
false, new_known_state must be exactly the original known_state, unchanged.
7. change_summary should be a short, concrete description of what changed, written for a general \
reader. Leave it null if material_change is false.
8. supporting_article_ids must list ONLY the ids of articles (from the supplied list) that \
actually support your material_change / change_summary decision. Never invent ids.
9. reason is a short internal note explaining your decision, for debugging — it is not shown to \
the user.

Output ONLY valid JSON matching this exact shape, with no commentary, no markdown fences, and no \
extra keys:

{
  "material_change": true,
  "condition_satisfied": false,
  "change_summary": "string or null",
  "new_known_state": "string",
  "reason": "string",
  "supporting_article_ids": ["string"]
}
"""


class WatchAnalysisError(Exception):
    """Raised when the model's watch-analysis output can't be trusted. Message is safe to show the user."""


class WatchAnalysisResult(BaseModel):
    material_change: bool
    condition_satisfied: bool
    change_summary: str | None = None
    new_known_state: str
    reason: str
    supporting_article_ids: list[str] = []


async def analyze_watch_update(
    *,
    headline: str,
    topic: str,
    known_state: str,
    watch_condition: str,
    major_developments_only: bool,
    last_checked_at: str | None,
    articles: list[Article],
    recent_developments: list[str] | None = None,
) -> WatchAnalysisResult:
    payload = {
        "headline": headline,
        "topic": topic,
        "known_state": known_state,
        "watch_condition": watch_condition,
        "major_developments_only": major_developments_only,
        "last_checked_at": last_checked_at,
        "recent_developments": recent_developments or [],
        "articles": [article.model_dump() for article in articles],
    }

    parsed = await send_json_message(SYSTEM_PROMPT, json.dumps(payload))

    try:
        return WatchAnalysisResult.model_validate(parsed)
    except ValidationError as exc:
        logger.error("Backboard watch-analysis JSON did not match expected schema: %s", type(exc).__name__)
        raise WatchAnalysisError("Couldn't analyze updates for this watch. Please try again.") from exc
