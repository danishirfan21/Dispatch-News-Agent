from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from .config import settings
from .db import get_db
from .models import BriefStory, ProfilePutRequest


async def find_user_by_email(email: str) -> dict | None:
    return await get_db().users.find_one({"email": email})


async def find_user_by_id(user_id: str) -> dict | None:
    object_id = _to_object_id(user_id)
    if not object_id:
        return None
    return await get_db().users.find_one({"_id": object_id})


async def create_user(email: str, password_hash: str) -> dict:
    doc = {
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_profile(user_id: str) -> dict | None:
    return await get_db().profiles.find_one({"user_id": user_id})


async def upsert_profile(user_id: str, profile: ProfilePutRequest) -> dict:
    now = datetime.now(timezone.utc)
    db = get_db()
    existing = await db.profiles.find_one({"user_id": user_id})

    update = {
        "user_id": user_id,
        "raw_interest_text": profile.raw_interest_text,
        "interests": [interest.model_dump() for interest in profile.interests],
        "excluded_topics": profile.excluded_topics,
        "updated_at": now,
    }
    if existing:
        await db.profiles.update_one({"user_id": user_id}, {"$set": update})
    else:
        update["created_at"] = now
        await db.profiles.insert_one(update)

    return await db.profiles.find_one({"user_id": user_id})


async def save_brief(user_id: str, stories: list[BriefStory]) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "generated_at": now,
        "stories": [story.model_dump() for story in stories],
    }
    await get_db().briefs.insert_one(doc)
    return doc


async def get_latest_brief(user_id: str) -> dict | None:
    return await get_db().briefs.find_one(
        {"user_id": user_id},
        sort=[("generated_at", -1)],
    )


async def find_story_in_latest_brief(user_id: str, story_id: str) -> dict | None:
    brief_doc = await get_latest_brief(user_id)
    if not brief_doc:
        return None
    for story in brief_doc["stories"]:
        if story["id"] == story_id:
            return story
    return None


async def find_watch_by_story(user_id: str, story_id: str) -> dict | None:
    return await get_db().watches.find_one({"user_id": user_id, "story_id": story_id})


async def create_watch(user_id: str, story: dict) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "story_id": story["id"],
        "topic": story["topic"],
        "headline": story["headline"],
        "summary": story["summary"],
        "sources": story["sources"],
        "published_at": story.get("published_at"),
        "known_state": story["summary"],
        "known_state_updated_at": now,
        "watch_condition": "",
        "major_developments_only": True,
        "status": "active",
        "development_status": "no_change",
        "latest_change": None,
        "last_checked_at": None,
        "next_check_at": now + timedelta(minutes=settings.watch_check_interval_minutes),
        "condition_satisfied_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await get_db().watches.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_watches(user_id: str) -> list[dict]:
    cursor = get_db().watches.find({"user_id": user_id}).sort("created_at", -1)
    return await cursor.to_list(length=None)


def _to_object_id(watch_id: str) -> ObjectId | None:
    try:
        return ObjectId(watch_id)
    except InvalidId:
        return None


async def get_watch(user_id: str, watch_id: str) -> dict | None:
    object_id = _to_object_id(watch_id)
    if not object_id:
        return None
    return await get_db().watches.find_one({"_id": object_id, "user_id": user_id})


async def update_watch(user_id: str, watch_id: str, updates: dict) -> dict | None:
    object_id = _to_object_id(watch_id)
    if not object_id:
        return None

    updates = {**updates, "updated_at": datetime.now(timezone.utc)}
    result = await get_db().watches.update_one(
        {"_id": object_id, "user_id": user_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        return None
    return await get_db().watches.find_one({"_id": object_id, "user_id": user_id})


async def delete_watch(user_id: str, watch_id: str) -> bool:
    object_id = _to_object_id(watch_id)
    if not object_id:
        return False
    result = await get_db().watches.delete_one({"_id": object_id, "user_id": user_id})
    return result.deleted_count > 0


async def find_due_watches(now: datetime, limit: int) -> list[dict]:
    cursor = (
        get_db()
        .watches.find({"status": "active", "next_check_at": {"$lte": now}})
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def create_development(
    *,
    user_id: str,
    watch_id: str,
    summary: str,
    known_state_before: str,
    known_state_after: str,
    condition_satisfied: bool,
    sources: list[dict],
    detected_at: datetime,
    trigger: str,
    notification_decision: str,
    notification_reason: str,
) -> dict:
    doc = {
        "user_id": user_id,
        "watch_id": watch_id,
        "summary": summary,
        "known_state_before": known_state_before,
        "known_state_after": known_state_after,
        "condition_satisfied": condition_satisfied,
        "sources": sources,
        "detected_at": detected_at,
        "trigger": trigger,
        "notification_decision": notification_decision,
        "notification_reason": notification_reason,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().watch_developments.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_developments(user_id: str, watch_id: str) -> list[dict]:
    cursor = get_db().watch_developments.find(
        {"user_id": user_id, "watch_id": watch_id}
    ).sort("detected_at", -1)
    return await cursor.to_list(length=None)


async def list_recent_development_summaries(watch_id: str, limit: int = 5) -> list[str]:
    cursor = (
        get_db()
        .watch_developments.find({"watch_id": watch_id}, {"summary": 1})
        .sort("detected_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [doc["summary"] for doc in docs if doc.get("summary")]


async def create_notification(doc: dict) -> dict | None:
    """Insert a pending notification; returns None if one already exists for
    this (development_id, type) pair — the unique index makes this idempotent
    so a retried or re-run check can never create a duplicate.
    """
    try:
        result = await get_db().notifications.insert_one(doc)
    except DuplicateKeyError:
        return None
    doc["_id"] = result.inserted_id
    return doc


async def get_watch_by_id(watch_id: str) -> dict | None:
    """Internal, trusted lookup with no user_id filter — only ever called by
    the notification-delivery worker with a watch_id taken from our own
    outbox record, never from user-supplied input."""
    object_id = _to_object_id(watch_id)
    if not object_id:
        return None
    return await get_db().watches.find_one({"_id": object_id})


async def get_development_by_id(development_id: str) -> dict | None:
    object_id = _to_object_id(development_id)
    if not object_id:
        return None
    return await get_db().watch_developments.find_one({"_id": object_id})


async def claim_pending_notification(now: datetime) -> dict | None:
    """Atomically claim one due pending notification (pending -> processing)
    so two concurrent delivery workers can never send the same notification
    twice."""
    return await get_db().notifications.find_one_and_update(
        {"status": "pending", "next_attempt_at": {"$lte": now}},
        {"$set": {"status": "processing", "last_attempt_at": now}},
        sort=[("next_attempt_at", 1)],
        return_document=ReturnDocument.AFTER,
    )


async def mark_notification_sent(notification_id: str, *, provider_message_id: str | None) -> None:
    update: dict = {"status": "sent", "sent_at": datetime.now(timezone.utc)}
    if provider_message_id:
        update["provider_message_id"] = provider_message_id
    await get_db().notifications.update_one({"_id": ObjectId(notification_id)}, {"$set": update})


async def schedule_notification_retry(
    notification_id: str, *, attempt_count: int, next_attempt_at: datetime, last_error_code: str
) -> None:
    await get_db().notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {
            "$set": {
                "status": "pending",
                "attempt_count": attempt_count,
                "next_attempt_at": next_attempt_at,
                "last_error_code": last_error_code,
            }
        },
    )


async def mark_notification_failed(notification_id: str, *, attempt_count: int, last_error_code: str) -> None:
    await get_db().notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {
            "$set": {
                "status": "failed",
                "failed_at": datetime.now(timezone.utc),
                "attempt_count": attempt_count,
                "last_error_code": last_error_code,
            }
        },
    )
