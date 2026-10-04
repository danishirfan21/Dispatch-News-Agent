from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from .db import get_db
from .models import BriefStory, ProfilePutRequest


async def find_user_by_email(email: str) -> dict | None:
    return await get_db().users.find_one({"email": email})


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
