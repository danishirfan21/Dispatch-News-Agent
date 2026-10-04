from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Cookie, HTTPException, Response

from .config import settings
from .db import get_db
from .security import decode_access_token

COOKIE_NAME = "dispatch_token"


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expires_minutes * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


class AuthenticatedUser:
    def __init__(self, id: str, email: str):
        self.id = id
        self.email = email


async def get_current_user(
    dispatch_token: str | None = Cookie(default=None),
) -> AuthenticatedUser:
    if not dispatch_token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user_id = decode_access_token(dispatch_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    try:
        object_id = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    db = get_db()
    user_doc = await db.users.find_one({"_id": object_id})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    return AuthenticatedUser(id=str(user_doc["_id"]), email=user_doc["email"])
