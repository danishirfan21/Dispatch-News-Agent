import hashlib
import logging
import re

import httpx

from ..config import settings
from ..models import Article, Interest

logger = logging.getLogger("serpapi")


class SerpApiError(Exception):
    """Raised for any SerpApi-related failure. Message is safe to show the user."""


def _build_query(interest: Interest) -> str:
    """Build a search query that keeps the interest's own geographic/topical
    specificity rather than genericizing it, while staying short."""
    terms = [interest.topic, *interest.search_terms]
    seen: set[str] = set()
    deduped: list[str] = []
    for term in terms:
        key = term.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(term.strip())
    # Keep it tight: the topic plus up to two extra search terms is enough
    # context for Google News without turning into an unwieldy query string.
    return " ".join(deduped[:3])


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _article_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


async def _fetch_google_news(client: httpx.AsyncClient, query: str, topic: str, limit: int) -> list[Article]:
    # Note: SerpApi's google_news engine rejects `so` (sort) when `q` is set,
    # so recency comes from the query itself (Google News ranks recent
    # coverage highly by default) rather than an explicit sort parameter.
    params = {
        "engine": "google_news",
        "q": query,
        "hl": "en",
        "api_key": settings.serpapi_api_key,
    }

    try:
        response = await client.get(settings.serpapi_base_url, params=params)
    except httpx.TimeoutException as exc:
        logger.error("SerpApi request timed out for a query: %s", type(exc).__name__)
        raise SerpApiError("The news search took too long to respond. Please try again.") from exc
    except httpx.RequestError as exc:
        logger.error("SerpApi request failed for a query: %s", type(exc).__name__)
        raise SerpApiError("Couldn't reach the news search service. Please try again.") from exc

    if response.status_code == 429:
        logger.error("SerpApi rate limit/quota exceeded")
        raise SerpApiError("The news search is temporarily rate-limited. Please try again shortly.")

    try:
        body = response.json()
    except ValueError as exc:
        logger.error("SerpApi response was not valid JSON: %s", type(exc).__name__)
        raise SerpApiError("The news search sent back something we couldn't read.") from exc

    if response.status_code != 200 or "error" in body:
        logger.error("SerpApi returned an error status=%s", response.status_code)
        raise SerpApiError("The news search service returned an error. Please try again.")

    results = body.get("news_results", [])
    articles: list[Article] = []
    for result in results[:limit]:
        url = result.get("link")
        title = result.get("title")
        if not url or not title:
            continue
        source = result.get("source", {})
        articles.append(
            Article(
                id=_article_id(url),
                topic=topic,
                title=title,
                source=source.get("name", "") if isinstance(source, dict) else "",
                url=url,
                published_at=result.get("iso_date") or result.get("date"),
                snippet=result.get("snippet"),
                thumbnail=result.get("thumbnail"),
            )
        )
    return articles


async def _search_one_interest(client: httpx.AsyncClient, interest: Interest) -> list[Article]:
    return await _fetch_google_news(
        client, _build_query(interest), interest.topic, settings.serpapi_results_per_interest
    )


def _dedupe_articles(articles: list[Article]) -> list[Article]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    deduped: list[Article] = []
    for article in articles:
        normalized_title = _normalize_title(article.title)
        if article.url in seen_urls or normalized_title in seen_titles:
            continue
        seen_urls.add(article.url)
        seen_titles.add(normalized_title)
        deduped.append(article)
    return deduped


async def search_news(interests: list[Interest]) -> list[Article]:
    if not settings.serpapi_api_key:
        logger.error("SerpApi search skipped: API key is not configured")
        raise SerpApiError("The news search isn't configured on the server yet.")

    all_articles: list[Article] = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        for interest in interests:
            all_articles.extend(await _search_one_interest(client, interest))

    return _dedupe_articles(all_articles)


async def search_news_for_query(query: str, topic: str, limit: int | None = None) -> list[Article]:
    """Single-query Google News search used for Watch update checks, where
    the query is derived server-side from the Watch itself (never from
    arbitrary frontend input)."""
    if not settings.serpapi_api_key:
        logger.error("SerpApi search skipped: API key is not configured")
        raise SerpApiError("The news search isn't configured on the server yet.")

    async with httpx.AsyncClient(timeout=20.0) as client:
        articles = await _fetch_google_news(
            client, query, topic, limit or settings.serpapi_results_per_interest
        )

    return _dedupe_articles(articles)
