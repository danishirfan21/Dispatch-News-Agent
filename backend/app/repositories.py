from datetime import datetime, timezone

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
