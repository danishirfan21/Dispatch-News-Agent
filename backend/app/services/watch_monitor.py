"""Reusable Watch update-checking service.

This is the single place that knows how to check one Watch for a material
change: retrieve fresh coverage, run the existing Backboard/Kimi analysis,
conservatively verify the result, and persist the outcome (Watch state,
durable development history, and a notification-outbox record when the
notification policy decides the user should be alerted).

Both the manual "Check for updates" endpoint and the automatic periodic
monitor call `check_watch_for_updates` — there is exactly one copy of this
orchestration logic.
"""

import difflib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .. import repositories
from ..config import settings
from ..models import BriefSource, CheckTrigger, NotificationDecision
from .backboard import BackboardError
from .serpapi import SerpApiError, search_news_for_query
from .watch_analysis import WatchAnalysisError, analyze_watch_update

logger = logging.getLogger("watch_monitor")

# Two development summaries whose wording overlaps this much are treated as
# describing the same real-world fact, even if Kimi still flagged a change.
_DUPLICATE_SIMILARITY_THRESHOLD = 0.6

# Re-exported so callers only need to import from this module.
__all__ = ["check_watch_for_updates", "run_due_watch_checks", "WatchCheckOutcome", "MonitorRunStats"]


@dataclass
class WatchCheckOutcome:
    watch_doc: dict
    material_change: bool
    condition_satisfied: bool
    change_summary: str | None
    sources: list[BriefSource]
    checked_at: datetime
    development_id: str | None
    notification_created: bool


@dataclass
class MonitorRunStats:
    checked: int = 0
    new_developments: int = 0
    notifications_created: int = 0
    failed: int = 0
    results: list[dict] = field(default_factory=list)


def _next_check_at(now: datetime) -> datetime:
    return now + timedelta(minutes=settings.watch_check_interval_minutes)


def _as_utc_isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _is_likely_duplicate(change_summary: str, recent_summaries: list[str]) -> bool:
    """Deterministic guard against recording the same development twice.

    `known_state` is the first line of defense (each check is evaluated
    against the state left by the previous one), but this catches the case
    where Kimi still claims a change despite it already being in recent
    history, without spending another model call.
    """
    normalized_new = change_summary.strip().lower()
    if not normalized_new:
        return False
    for previous in recent_summaries:
        normalized_previous = previous.strip().lower()
        if not normalized_previous:
            continue
        ratio = difflib.SequenceMatcher(None, normalized_new, normalized_previous).ratio()
        if ratio >= _DUPLICATE_SIMILARITY_THRESHOLD:
            return True
    return False


def _build_notification_content(watch_doc: dict, development_doc: dict) -> dict:
    """Deterministic notification copy — no model call."""
    headline = watch_doc.get("headline", "").strip()
    title_subject = headline if len(headline) <= 60 else f"{headline[:57]}..."
    title = f"New development: {title_subject}"

    body = development_doc["summary"]
    if development_doc.get("condition_satisfied") and (watch_doc.get("watch_condition") or "").strip():
        body = f"{body} Your watch condition has been met."

    return {
        "user_id": watch_doc["user_id"],
        "watch_id": str(watch_doc["_id"]),
        "development_id": str(development_doc["_id"]),
        "type": "watch_development",
        "title": title,
        "body": body,
        "sources": development_doc["sources"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "sent_at": None,
        "failed_at": None,
    }


def _decide_notification(watch_doc: dict, condition_satisfied: bool) -> tuple[NotificationDecision, str]:
    watch_condition = (watch_doc.get("watch_condition") or "").strip()

    if not watch_condition:
        return "notify", "Material change detected; no custom watch condition is set."

    if not condition_satisfied:
        return "none", "Material change detected but the custom watch condition is not yet satisfied."

    if watch_doc.get("condition_satisfied_at"):
        return "none", "Watch condition remains satisfied; already notified when it was first met."

    return "notify", "Watch condition satisfied for the first time."


async def check_watch_for_updates(watch_doc: dict, *, trigger: CheckTrigger) -> WatchCheckOutcome:
    """Run the full check flow for one Watch and persist the outcome.

    Raises SerpApiError, BackboardError, or WatchAnalysisError on provider
    failure; callers are responsible for turning that into an HTTP error
    (manual) or isolating/rescheduling it (automatic).
    """
    user_id = watch_doc["user_id"]
    watch_id = str(watch_doc["_id"])
    existing_urls = {source.get("url") for source in watch_doc.get("sources", []) if source.get("url")}

    articles = await search_news_for_query(watch_doc["headline"], watch_doc["topic"])
    fresh_articles = [article for article in articles if article.url not in existing_urls]

    now = datetime.now(timezone.utc)

    if not fresh_articles:
        updated_doc = await repositories.update_watch(
            user_id,
            watch_id,
            {
                "last_checked_at": now,
                "development_status": "no_change",
                "next_check_at": _next_check_at(now),
            },
        )
        return WatchCheckOutcome(
            watch_doc=updated_doc or watch_doc,
            material_change=False,
            condition_satisfied=False,
            change_summary=None,
            sources=[],
            checked_at=now,
            development_id=None,
            notification_created=False,
        )

    recent_summaries = await repositories.list_recent_development_summaries(watch_id, limit=5)
    last_checked_at_iso = (
        _as_utc_isoformat(watch_doc["last_checked_at"]) if watch_doc.get("last_checked_at") else None
    )

    analysis = await analyze_watch_update(
        headline=watch_doc["headline"],
        topic=watch_doc["topic"],
        known_state=watch_doc["known_state"],
        watch_condition=watch_doc.get("watch_condition", ""),
        major_developments_only=watch_doc.get("major_developments_only", True),
        last_checked_at=last_checked_at_iso,
        articles=fresh_articles,
        recent_developments=recent_summaries,
    )

    articles_by_id = {article.id: article for article in fresh_articles}
    supporting = [
        articles_by_id[article_id] for article_id in analysis.supporting_article_ids if article_id in articles_by_id
    ]

    change_summary = analysis.change_summary or ""

    # Conservative by design: only trust a claimed material change when the
    # model cited verifiable evidence, and when it isn't just re-describing a
    # development we've already recorded.
    is_verified = analysis.material_change and bool(supporting)
    is_duplicate = is_verified and _is_likely_duplicate(change_summary, recent_summaries)

    if not is_verified or is_duplicate:
        updated_doc = await repositories.update_watch(
            user_id,
            watch_id,
            {
                "last_checked_at": now,
                "development_status": "no_change",
                "next_check_at": _next_check_at(now),
            },
        )
        return WatchCheckOutcome(
            watch_doc=updated_doc or watch_doc,
            material_change=False,
            condition_satisfied=False,
            change_summary=None,
            sources=[],
            checked_at=now,
            development_id=None,
            notification_created=False,
        )

    seen_source_names: set[str] = set()
    change_sources: list[BriefSource] = []
    for article in supporting:
        if article.source in seen_source_names:
            continue
        seen_source_names.add(article.source)
        change_sources.append(BriefSource(name=article.source, url=article.url))

    notification_decision, notification_reason = _decide_notification(watch_doc, analysis.condition_satisfied)

    watch_updates: dict = {
        "last_checked_at": now,
        "development_status": "new_development",
        "known_state": analysis.new_known_state,
        "known_state_updated_at": now,
        "latest_change": {
            "summary": change_summary,
            "detected_at": now,
            "sources": [source.model_dump() for source in change_sources],
        },
        "next_check_at": _next_check_at(now),
    }
    if notification_decision == "notify" and (watch_doc.get("watch_condition") or "").strip() and analysis.condition_satisfied:
        watch_updates["condition_satisfied_at"] = now

    updated_doc = await repositories.update_watch(user_id, watch_id, watch_updates)
    if updated_doc is None:
        # Watch was deleted mid-check; nothing left to persist history against.
        return WatchCheckOutcome(
            watch_doc=watch_doc,
            material_change=False,
            condition_satisfied=False,
            change_summary=None,
            sources=[],
            checked_at=now,
            development_id=None,
            notification_created=False,
        )

    development_doc = await repositories.create_development(
        user_id=user_id,
        watch_id=watch_id,
        summary=change_summary,
        known_state_before=watch_doc["known_state"],
        known_state_after=analysis.new_known_state,
        condition_satisfied=analysis.condition_satisfied,
        sources=[source.model_dump() for source in change_sources],
        detected_at=now,
        trigger=trigger,
        notification_decision=notification_decision,
        notification_reason=notification_reason,
    )

    notification_created = False
    if notification_decision == "notify":
        notification_doc = _build_notification_content(updated_doc, development_doc)
        created = await repositories.create_notification(notification_doc)
        notification_created = created is not None

    return WatchCheckOutcome(
        watch_doc=updated_doc,
        material_change=True,
        condition_satisfied=analysis.condition_satisfied,
        change_summary=change_summary,
        sources=change_sources,
        checked_at=now,
        development_id=str(development_doc["_id"]),
        notification_created=notification_created,
    )


async def run_due_watch_checks() -> MonitorRunStats:
    """Process every active Watch currently due for an automatic check.

    Failures are isolated per-Watch: a provider error for one Watch is
    rescheduled conservatively and never stops the rest of the batch, and
    never mutates that Watch's known_state/development history.
    """
    now = datetime.now(timezone.utc)
    due_watches = await repositories.find_due_watches(now, settings.watch_monitor_batch_size)

    stats = MonitorRunStats()

    for watch_doc in due_watches:
        watch_id = str(watch_doc["_id"])
        stats.checked += 1
        try:
            outcome = await check_watch_for_updates(watch_doc, trigger="automatic")
        except (SerpApiError, BackboardError, WatchAnalysisError) as exc:
            stats.failed += 1
            logger.warning("Automatic check failed for watch %s: %s", watch_id, type(exc).__name__)
            try:
                await repositories.update_watch(
                    watch_doc["user_id"],
                    watch_id,
                    {"next_check_at": _next_check_at(now)},
                )
            except Exception:
                logger.exception("Failed to reschedule watch %s after a failed check", watch_id)
            stats.results.append({"watch_id": watch_id, "status": "failed", "notification_created": False})
            continue
        except Exception:
            stats.failed += 1
            logger.exception("Unexpected error during automatic check for watch %s", watch_id)
            try:
                await repositories.update_watch(
                    watch_doc["user_id"],
                    watch_id,
                    {"next_check_at": _next_check_at(now)},
                )
            except Exception:
                logger.exception("Failed to reschedule watch %s after a failed check", watch_id)
            stats.results.append({"watch_id": watch_id, "status": "failed", "notification_created": False})
            continue

        if outcome.material_change:
            stats.new_developments += 1
            if outcome.notification_created:
                stats.notifications_created += 1
            status = "new_development"
        else:
            status = "no_change"

        stats.results.append(
            {"watch_id": watch_id, "status": status, "notification_created": outcome.notification_created}
        )

    return stats
