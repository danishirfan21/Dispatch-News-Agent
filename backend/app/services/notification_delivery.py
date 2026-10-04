"""Reusable email-delivery worker for the notifications outbox.

Kept entirely separate from watch_monitor.check_watch_for_updates(): Watch
monitoring only ever creates a durable `pending` notification record, and
this module is the single place that consumes that outbox and sends mail
through Mailjet. A Mailjet outage can never affect Watch-checking
reliability, and a Watch-checking failure can never lose a notification —
the two transactions don't share a call stack.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .. import repositories
from ..config import settings
from .email import EmailError, build_email_content, send_email

logger = logging.getLogger("notification_delivery")

MAX_ATTEMPTS = 3
# attempt 1 -> retry in 5 min, attempt 2 -> retry in 15 min, attempt 3 -> terminal failure.
_RETRY_BACKOFF_MINUTES = {1: 5, 2: 15}

__all__ = ["deliver_pending_notifications", "DeliveryStats"]


@dataclass
class DeliveryStats:
    processed: int = 0
    sent: int = 0
    retry_scheduled: int = 0
    failed: int = 0


def _retry_delay(attempt_count: int) -> timedelta:
    return timedelta(minutes=_RETRY_BACKOFF_MINUTES.get(attempt_count, 15))


async def _deliver_one(notification_doc: dict) -> str:
    """Delivers one already-claimed (status=processing) notification.

    Returns "sent", "retry_scheduled", or "failed". Never raises for a
    provider/data failure — those are handled and recorded; only a truly
    unexpected error propagates, and the caller isolates that per-notification.
    """
    notification_id = str(notification_doc["_id"])
    attempt_count = notification_doc.get("attempt_count", 0) + 1

    user_doc = await repositories.find_user_by_id(notification_doc["user_id"])
    if not user_doc or not user_doc.get("email"):
        logger.warning("Notification %s has no resolvable recipient; failing safely", notification_id)
        await repositories.mark_notification_failed(
            notification_id, attempt_count=attempt_count, last_error_code="missing_user"
        )
        return "failed"

    watch_doc = await repositories.get_watch_by_id(notification_doc["watch_id"])
    development_doc = await repositories.get_development_by_id(notification_doc["development_id"])
    if not watch_doc or not development_doc:
        logger.warning("Notification %s is missing Watch/development context; failing safely", notification_id)
        await repositories.mark_notification_failed(
            notification_id, attempt_count=attempt_count, last_error_code="missing_context"
        )
        return "failed"

    subject, text_body, html_body = build_email_content(
        watch_headline=watch_doc.get("headline", ""),
        development_summary=notification_doc["body"],
        watch_condition=watch_doc.get("watch_condition", ""),
        condition_satisfied=development_doc.get("condition_satisfied", False),
        sources=notification_doc.get("sources", []),
    )

    try:
        provider_message_id = await send_email(
            to_email=user_doc["email"], subject=subject, text_body=text_body, html_body=html_body
        )
    except EmailError as exc:
        logger.warning(
            "Email delivery failed for notification %s (attempt %d, category=%s)",
            notification_id,
            attempt_count,
            exc.category,
        )
        if exc.retryable and attempt_count < MAX_ATTEMPTS:
            next_attempt_at = datetime.now(timezone.utc) + _retry_delay(attempt_count)
            await repositories.schedule_notification_retry(
                notification_id,
                attempt_count=attempt_count,
                next_attempt_at=next_attempt_at,
                last_error_code=exc.category,
            )
            return "retry_scheduled"

        await repositories.mark_notification_failed(
            notification_id, attempt_count=attempt_count, last_error_code=exc.category
        )
        return "failed"

    await repositories.mark_notification_sent(notification_id, provider_message_id=provider_message_id)
    return "sent"


async def deliver_pending_notifications() -> DeliveryStats:
    """Processes a bounded batch of due pending notifications.

    Each notification is atomically claimed (pending -> processing) before
    being touched, so two concurrent runs can never send the same email
    twice. One notification's failure is isolated and never stops the batch.
    """
    stats = DeliveryStats()

    for _ in range(settings.notification_delivery_batch_size):
        now = datetime.now(timezone.utc)
        claimed = await repositories.claim_pending_notification(now)
        if not claimed:
            break

        stats.processed += 1
        notification_id = str(claimed["_id"])
        try:
            outcome = await _deliver_one(claimed)
        except Exception:
            logger.exception("Unexpected error delivering notification %s", notification_id)
            try:
                attempt_count = claimed.get("attempt_count", 0) + 1
                await repositories.mark_notification_failed(
                    notification_id, attempt_count=attempt_count, last_error_code="unexpected_error"
                )
            except Exception:
                logger.exception("Failed to record failure for notification %s", notification_id)
            stats.failed += 1
            continue

        if outcome == "sent":
            stats.sent += 1
        elif outcome == "retry_scheduled":
            stats.retry_scheduled += 1
        else:
            stats.failed += 1

    return stats
