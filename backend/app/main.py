import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo.errors import DuplicateKeyError

from . import repositories
from .auth import AuthenticatedUser, clear_auth_cookie, get_current_user, set_auth_cookie
from .config import settings
from .db import create_indexes
from .models import (
    BriefAudioResponse,
    BriefGenerateRequest,
    BriefGenerateResponse,
    BriefResponse,
    BriefSource,
    LoginRequest,
    MonitorRunResponse,
    NewsSearchRequest,
    NewsSearchResponse,
    NotificationDeliveryResponse,
    ParseInterestsRequest,
    ParseInterestsResponse,
    ProfilePutRequest,
    ProfileResponse,
    RegisterRequest,
    UserPublic,
    VoiceTranscribeResponse,
    WatchCheckResponse,
    WatchCheckResult,
    WatchCreateRequest,
    WatchDevelopmentResponse,
    WatchDevelopmentsResponse,
    WatchLatestChange,
    WatchPatchRequest,
    WatchResponse,
)
from .security import create_access_token, hash_password, normalize_email, verify_password
from .services.backboard import BackboardError, parse_interests
from .services.brief import generate_brief
from .services.elevenlabs import ElevenLabsError, synthesize_speech_with_timestamps, transcribe_audio
from .services.narration import build_narration, map_segment_timings
from .services.notification_delivery import deliver_pending_notifications
from .services.serpapi import SerpApiError, search_news
from .services.watch_analysis import WatchAnalysisError
from .services.watch_monitor import check_watch_for_updates, run_due_watch_checks

app = FastAPI(title="Dispatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await create_indexes()


@app.get("/api/health")
async def health_endpoint() -> dict:
    return {"status": "ok"}


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


@app.post("/api/voice/transcribe", response_model=VoiceTranscribeResponse)
async def voice_transcribe_endpoint(
    file: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user)
) -> VoiceTranscribeResponse:
    audio_bytes = await file.read()

    try:
        result = await transcribe_audio(audio_bytes, file.content_type or "")
    except ElevenLabsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return VoiceTranscribeResponse(**result)


@app.get("/api/brief/audio", response_model=BriefAudioResponse)
async def brief_audio_endpoint(user: AuthenticatedUser = Depends(get_current_user)) -> BriefAudioResponse:
    brief_doc = await repositories.get_latest_brief(user.id)
    if not brief_doc:
        raise HTTPException(status_code=404, detail="No saved brief yet.")

    narration_text, segments_meta = build_narration(brief_doc["stories"])
    if not narration_text.strip():
        raise HTTPException(status_code=404, detail="Your brief doesn't have anything to narrate yet.")

    try:
        tts_result = await synthesize_speech_with_timestamps(narration_text)
    except ElevenLabsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    segments = map_segment_timings(
        segments_meta,
        narration_text,
        tts_result["characters"],
        tts_result["start_times"],
        tts_result["end_times"],
    )

    return BriefAudioResponse(audio_base64=tts_result["audio_base64"], mime_type="audio/mpeg", segments=segments)


def _as_utc_isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _to_latest_change(value: object) -> WatchLatestChange | None:
    if not isinstance(value, dict):
        return None
    detected_at = value.get("detected_at")
    return WatchLatestChange(
        summary=value.get("summary", ""),
        detected_at=_as_utc_isoformat(detected_at) if isinstance(detected_at, datetime) else str(detected_at or ""),
        sources=[BriefSource(**source) for source in value.get("sources", [])],
    )


def _to_watch_response(doc: dict) -> WatchResponse:
    return WatchResponse(
        id=str(doc["_id"]),
        story_id=doc["story_id"],
        topic=doc["topic"],
        headline=doc["headline"],
        summary=doc["summary"],
        sources=doc["sources"],
        published_at=doc.get("published_at"),
        known_state=doc["known_state"],
        known_state_updated_at=_as_utc_isoformat(doc["known_state_updated_at"])
        if doc.get("known_state_updated_at")
        else _as_utc_isoformat(doc["created_at"]),
        watch_condition=doc["watch_condition"],
        major_developments_only=doc["major_developments_only"],
        status=doc["status"],
        development_status=doc.get("development_status", "no_change"),
        latest_change=_to_latest_change(doc.get("latest_change")),
        last_checked_at=_as_utc_isoformat(doc["last_checked_at"]) if doc.get("last_checked_at") else None,
        created_at=_as_utc_isoformat(doc["created_at"]),
        updated_at=_as_utc_isoformat(doc["updated_at"]),
    )


@app.post("/api/watches", response_model=WatchResponse)
async def create_watch_endpoint(
    request: WatchCreateRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> WatchResponse:
    existing = await repositories.find_watch_by_story(user.id, request.story_id)
    if existing:
        return _to_watch_response(existing)

    story = await repositories.find_story_in_latest_brief(user.id, request.story_id)
    if not story:
        raise HTTPException(status_code=404, detail="That story isn't in your saved brief.")

    try:
        watch_doc = await repositories.create_watch(user.id, story)
    except DuplicateKeyError:
        existing = await repositories.find_watch_by_story(user.id, request.story_id)
        if not existing:
            raise
        return _to_watch_response(existing)

    return _to_watch_response(watch_doc)


@app.get("/api/watches", response_model=list[WatchResponse])
async def list_watches_endpoint(user: AuthenticatedUser = Depends(get_current_user)) -> list[WatchResponse]:
    watch_docs = await repositories.list_watches(user.id)
    return [_to_watch_response(doc) for doc in watch_docs]


@app.get("/api/watches/{watch_id}", response_model=WatchResponse)
async def get_watch_endpoint(
    watch_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> WatchResponse:
    watch_doc = await repositories.get_watch(user.id, watch_id)
    if not watch_doc:
        raise HTTPException(status_code=404, detail="Watch not found.")
    return _to_watch_response(watch_doc)


@app.patch("/api/watches/{watch_id}", response_model=WatchResponse)
async def patch_watch_endpoint(
    watch_id: str, request: WatchPatchRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> WatchResponse:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        watch_doc = await repositories.get_watch(user.id, watch_id)
    else:
        current_doc = await repositories.get_watch(user.id, watch_id)
        if not current_doc:
            raise HTTPException(status_code=404, detail="Watch not found.")

        if "watch_condition" in updates and updates["watch_condition"] != current_doc.get("watch_condition", ""):
            updates["condition_satisfied_at"] = None

        if (
            updates.get("status") == "active"
            and current_doc.get("status") == "paused"
        ):
            updates["next_check_at"] = datetime.now(timezone.utc) + timedelta(
                minutes=settings.watch_check_interval_minutes
            )

        watch_doc = await repositories.update_watch(user.id, watch_id, updates)

    if not watch_doc:
        raise HTTPException(status_code=404, detail="Watch not found.")
    return _to_watch_response(watch_doc)


@app.delete("/api/watches/{watch_id}")
async def delete_watch_endpoint(watch_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    deleted = await repositories.delete_watch(user.id, watch_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watch not found.")
    return {"ok": True}


@app.post("/api/watches/{watch_id}/check", response_model=WatchCheckResponse)
async def check_watch_endpoint(
    watch_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> WatchCheckResponse:
    watch_doc = await repositories.get_watch(user.id, watch_id)
    if not watch_doc:
        raise HTTPException(status_code=404, detail="Watch not found.")

    if watch_doc["status"] == "paused":
        raise HTTPException(status_code=409, detail="This watch is paused. Resume it to check for updates.")

    try:
        outcome = await check_watch_for_updates(watch_doc, trigger="manual")
    except SerpApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (BackboardError, WatchAnalysisError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return WatchCheckResponse(
        watch=_to_watch_response(outcome.watch_doc),
        check=WatchCheckResult(
            material_change=outcome.material_change,
            condition_satisfied=outcome.condition_satisfied,
            change_summary=outcome.change_summary,
            checked_at=_as_utc_isoformat(outcome.checked_at),
            sources=outcome.sources,
        ),
    )


def _to_development_response(doc: dict) -> WatchDevelopmentResponse:
    return WatchDevelopmentResponse(
        id=str(doc["_id"]),
        summary=doc["summary"],
        known_state_before=doc["known_state_before"],
        known_state_after=doc["known_state_after"],
        condition_satisfied=doc["condition_satisfied"],
        sources=[BriefSource(**source) for source in doc.get("sources", [])],
        detected_at=_as_utc_isoformat(doc["detected_at"]),
        trigger=doc["trigger"],
    )


@app.get("/api/watches/{watch_id}/developments", response_model=WatchDevelopmentsResponse)
async def list_watch_developments_endpoint(
    watch_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> WatchDevelopmentsResponse:
    watch_doc = await repositories.get_watch(user.id, watch_id)
    if not watch_doc:
        raise HTTPException(status_code=404, detail="Watch not found.")

    development_docs = await repositories.list_developments(user.id, watch_id)
    return WatchDevelopmentsResponse(developments=[_to_development_response(doc) for doc in development_docs])


async def verify_monitor_secret(authorization: str | None = Header(default=None)) -> None:
    expected = settings.monitor_secret
    provided = (authorization or "").removeprefix("Bearer ").strip()
    if not expected or not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized.")


@app.post("/api/internal/monitor/run", response_model=MonitorRunResponse, dependencies=[Depends(verify_monitor_secret)])
async def run_monitor_endpoint() -> MonitorRunResponse:
    stats = await run_due_watch_checks()
    return MonitorRunResponse(
        checked=stats.checked,
        new_developments=stats.new_developments,
        notifications_created=stats.notifications_created,
        failed=stats.failed,
    )


@app.post(
    "/api/internal/notifications/deliver",
    response_model=NotificationDeliveryResponse,
    dependencies=[Depends(verify_monitor_secret)],
)
async def deliver_notifications_endpoint() -> NotificationDeliveryResponse:
    stats = await deliver_pending_notifications()
    return NotificationDeliveryResponse(
        processed=stats.processed,
        sent=stats.sent,
        retry_scheduled=stats.retry_scheduled,
        failed=stats.failed,
    )


# Built React app (repo_root/dist), produced by `npm run build`. Serving it
# here is what lets the frontend and API share one Render origin. Only
# mounted when the build actually exists, so running the backend alone in
# local development (no `dist/`) is unaffected.
FRONTEND_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "dist"

if FRONTEND_DIST_DIR.is_dir():
    app.mount(
        "/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="frontend-assets"
    )

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str) -> FileResponse:
        # Never let this catch-all mask a real API 404 as the SPA shell.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")

        candidate = FRONTEND_DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)

        # Any other path is a client-side route (e.g. /watching/123) — hand
        # it to the React app, which resolves it with its own router.
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
