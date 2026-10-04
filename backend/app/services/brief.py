import hashlib
import json
import logging

from pydantic import BaseModel, ValidationError

from ..models import Article, BriefSource, BriefStory, Importance, ParseInterestsResponse
from .backboard import BackboardError, send_json_message

logger = logging.getLogger("brief")

SYSTEM_PROMPT = """You curate a short personal news brief from a user's stated interests and a \
set of retrieved news articles.

You will receive two things as JSON in the user message:
- "interest_profile": the topics the user confirmed they want, each with a priority, plus \
topics they explicitly do NOT want.
- "articles": a small set of real news articles retrieved for those topics. Each article has \
an "id", "topic" (which interest it was retrieved for), "title", "source", "url", \
"published_at", and sometimes a "snippet".

Your job, in order:
1. Discard any article that is only weakly or tangentially related to the interest it was \
retrieved for. Merely mentioning a place or name is not enough — the article's main subject \
must genuinely match the user's stated interest. Be aggressive about cutting weak matches.
2. Among the articles that remain, find groups that cover the same underlying real-world \
event (e.g. the same announcement reported by several outlets) and merge each group into one \
story, citing all of their article ids.
3. Prefer recent developments over old ones, and prefer substantive developments over \
commentary, opinion pieces, or filler.
4. Prefer stories backed by multiple independent sources when that's available in the data.
5. Rank the resulting stories by how relevant and significant they are to THIS user, given \
their stated priorities.
6. Return AT MOST 5 stories. If fewer than 5 genuinely qualify, return fewer — never pad the \
list with weak stories to reach 5. If nothing qualifies, return an empty list.

Factual safety — this is extremely important:
- You may ONLY use facts present in the supplied article titles, snippets, and metadata.
- Do not invent or infer quotes, numbers, dates, causes, motives, or outcomes that are not \
directly stated in the supplied text.
- If the available text is too thin to support a detailed summary, write a shorter, more \
conservative summary instead of guessing or elaborating.

For each selected story, output:
{
  "topic": "one of the user's interest topics this story belongs to",
  "headline": "a short, concrete, factual headline (your own wording, not copied verbatim)",
  "summary": "2-4 sentences, grounded only in the supplied article text",
  "why_this_matters_to_you": "1-2 sentences connecting it to the user's specific stated interest",
  "source_article_ids": ["the", "ids", "of", "every", "article", "id", "that", "covers", "this", "story"],
  "importance": "high" | "medium" | "low"
}

Output ONLY valid JSON matching this exact shape, with no commentary, no markdown fences, and \
no extra keys:

{
  "stories": [ { ...as above... } ]
}
"""


class _ModelStory(BaseModel):
    topic: str
    headline: str
    summary: str
    why_this_matters_to_you: str
    source_article_ids: list[str]
    importance: Importance


class _ModelBriefResult(BaseModel):
    stories: list[_ModelStory]


def _story_id(headline: str, index: int) -> str:
    return hashlib.sha1(f"{index}:{headline}".encode("utf-8")).hexdigest()[:16]


async def generate_brief(
    interest_profile: ParseInterestsResponse, articles: list[Article]
) -> list[BriefStory]:
    if not articles:
        return []

    articles_by_id = {article.id: article for article in articles}

    user_content_payload = {
        "interest_profile": interest_profile.model_dump(),
        "articles": [article.model_dump() for article in articles],
    }
    parsed = await send_json_message(SYSTEM_PROMPT, json.dumps(user_content_payload))

    try:
        model_result = _ModelBriefResult.model_validate(parsed)
    except ValidationError as exc:
        logger.error("Backboard brief JSON did not match expected schema: %s", type(exc).__name__)
        raise BackboardError("The AI service sent back something we couldn't read.") from exc

    stories: list[BriefStory] = []
    for index, model_story in enumerate(model_result.stories[:5]):
        matched = [
            articles_by_id[article_id]
            for article_id in model_story.source_article_ids
            if article_id in articles_by_id
        ]
        if not matched:
            # The model cited only articles we never sent it — skip rather
            # than ship a story with fabricated/unverifiable sourcing.
            continue

        seen_source_names: set[str] = set()
        sources: list[BriefSource] = []
        for article in matched:
            if article.source in seen_source_names:
                continue
            seen_source_names.add(article.source)
            sources.append(BriefSource(name=article.source, url=article.url))

        published_at = max(
            (article.published_at for article in matched if article.published_at),
            default=None,
        )

        stories.append(
            BriefStory(
                id=_story_id(model_story.headline, index),
                topic=model_story.topic,
                headline=model_story.headline,
                summary=model_story.summary,
                why_this_matters_to_you=model_story.why_this_matters_to_you,
                source_article_ids=[article.id for article in matched],
                sources=sources,
                published_at=published_at,
                importance=model_story.importance,
            )
        )

    return stories
