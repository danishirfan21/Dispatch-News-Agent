from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import DuplicateKeyError

from . import repositories
from .auth import AuthenticatedUser, clear_auth_cookie, get_current_user, set_auth_cookie
from .config import settings
from .db import create_indexes
from .models import (
    BriefGenerateRequest,
    BriefGenerateResponse,
    BriefResponse,
    LoginRequest,
    NewsSearchRequest,
    NewsSearchResponse,
    ParseInterestsRequest,
    ParseInterestsResponse,
    ProfilePutRequest,
    ProfileResponse,
    RegisterRequest,
    UserPublic,
)
from .security import create_access_token, hash_password, normalize_email, verify_password
from .services.backboard import BackboardError, parse_interests
from .services.brief import generate_brief
from .services.serpapi import SerpApiError, search_news

app = FastAPI(title="Dispatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await create_indexes()


@app.post("/api/auth/register", response_model=UserPublic)
async def register_endpoint(request: RegisterRequest, response: Response) -> UserPublic:
    email = normalize_email(request.email)

    if await repositories.find_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    try:
        user_doc = await repositories.create_user(email, hash_password(request.password))
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    token = create_access_token(str(user_doc["_id"]))
    set_auth_cookie(response, token)
    return UserPublic(id=str(user_doc["_id"]), email=user_doc["email"])


@app.post("/api/auth/login", response_model=UserPublic)
async def login_endpoint(request: LoginRequest, response: Response) -> UserPublic:
    email = normalize_email(request.email)
    user_doc = await repositories.find_user_by_email(email)

    if not user_doc or not verify_password(request.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(str(user_doc["_id"]))
    set_auth_cookie(response, token)
    return UserPublic(id=str(user_doc["_id"]), email=user_doc["email"])


@app.post("/api/auth/logout")
async def logout_endpoint(response: Response) -> dict:
    clear_auth_cookie(response)
    return {"ok": True}


@app.get("/api/auth/me", response_model=UserPublic)
async def me_endpoint(user: AuthenticatedUser = Depends(get_current_user)) -> UserPublic:
    return UserPublic(id=user.id, email=user.email)


@app.get("/api/profile", response_model=ProfileResponse)
async def get_profile_endpoint(user: AuthenticatedUser = Depends(get_current_user)) -> ProfileResponse:
    profile_doc = await repositories.get_profile(user.id)
    if not profile_doc:
        raise HTTPException(status_code=404, detail="No saved profile yet.")

    return ProfileResponse(
        raw_interest_text=profile_doc["raw_interest_text"],
        interests=profile_doc["interests"],
        excluded_topics=profile_doc["excluded_topics"],
        updated_at=profile_doc["updated_at"].isoformat(),
    )


@app.put("/api/profile", response_model=ProfileResponse)
async def put_profile_endpoint(
    request: ProfilePutRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> ProfileResponse:
    profile_doc = await repositories.upsert_profile(user.id, request)
    return ProfileResponse(
        raw_interest_text=profile_doc["raw_interest_text"],
        interests=profile_doc["interests"],
        excluded_topics=profile_doc["excluded_topics"],
        updated_at=profile_doc["updated_at"].isoformat(),
    )


@app.post("/api/interests/parse", response_model=ParseInterestsResponse)
async def parse_interests_endpoint(request: ParseInterestsRequest) -> ParseInterestsResponse:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Tell us a bit about what you're interested in first.")

    try:
        return await parse_interests(text)
    except BackboardError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/news/search", response_model=NewsSearchResponse)
async def news_search_endpoint(request: NewsSearchRequest) -> NewsSearchResponse:
    if not request.interests:
        raise HTTPException(status_code=400, detail="No interests to search for.")

    try:
        articles = await search_news(request.interests)
    except SerpApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not articles:
        raise HTTPException(status_code=404, detail="No current news found for these interests.")

    return NewsSearchResponse(articles=articles)


@app.post("/api/brief/generate", response_model=BriefGenerateResponse)
async def brief_generate_endpoint(
    request: BriefGenerateRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> BriefGenerateResponse:
    if not request.articles:
        raise HTTPException(status_code=400, detail="No articles to curate.")

    try:
        stories = await generate_brief(request.interest_profile, request.articles)
    except BackboardError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not stories:
        raise HTTPException(
            status_code=404,
            detail="Couldn't find any stories strongly related to your interests right now.",
        )

    await repositories.save_brief(user.id, stories)

    return BriefGenerateResponse(stories=stories)


@app.get("/api/brief/latest", response_model=BriefResponse)
async def brief_latest_endpoint(user: AuthenticatedUser = Depends(get_current_user)) -> BriefResponse:
    brief_doc = await repositories.get_latest_brief(user.id)
    if not brief_doc:
        raise HTTPException(status_code=404, detail="No saved brief yet.")

    return BriefResponse(
        generated_at=brief_doc["generated_at"].isoformat(),
        stories=brief_doc["stories"],
    )
