from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Priority = Literal["high", "medium", "low"]


class ParseInterestsRequest(BaseModel):
    text: str


class Interest(BaseModel):
    topic: str
    priority: Priority
    search_terms: list[str] = Field(default_factory=list)


class ParseInterestsResponse(BaseModel):
    interests: list[Interest]
    excluded_topics: list[str] = Field(default_factory=list)


class NewsSearchRequest(BaseModel):
    interests: list[Interest]
    excluded_topics: list[str] = Field(default_factory=list)


class Article(BaseModel):
    id: str
    topic: str
    title: str
    source: str
    url: str
    published_at: str | None = None
    snippet: str | None = None
    thumbnail: str | None = None


class NewsSearchResponse(BaseModel):
    articles: list[Article]


class BriefGenerateRequest(BaseModel):
    interest_profile: ParseInterestsResponse
    articles: list[Article]


class BriefSource(BaseModel):
    name: str
    url: str


Importance = Literal["high", "medium", "low"]


class BriefStory(BaseModel):
    id: str
    topic: str
    headline: str
    summary: str
    why_this_matters_to_you: str
    source_article_ids: list[str]
    sources: list[BriefSource]
    published_at: str | None = None
    importance: Importance


class BriefGenerateResponse(BaseModel):
    stories: list[BriefStory]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: str


class ProfilePutRequest(BaseModel):
    raw_interest_text: str
    interests: list[Interest]
    excluded_topics: list[str] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    raw_interest_text: str
    interests: list[Interest]
    excluded_topics: list[str] = Field(default_factory=list)
    updated_at: str


class BriefResponse(BaseModel):
    generated_at: str
    stories: list[BriefStory]


class VoiceTranscribeResponse(BaseModel):
    text: str
    language_code: str


SegmentType = Literal["headline", "summary"]


class BriefAudioSegment(BaseModel):
    story_id: str
    type: SegmentType
    text: str
    start: float
    end: float


class BriefAudioResponse(BaseModel):
    audio_base64: str
    mime_type: str
    segments: list[BriefAudioSegment]


WatchStatus = Literal["active", "paused"]


class WatchCreateRequest(BaseModel):
    story_id: str


class WatchPatchRequest(BaseModel):
    watch_condition: str | None = None
    major_developments_only: bool | None = None
    status: WatchStatus | None = None


class WatchResponse(BaseModel):
    id: str
    story_id: str
    topic: str
    headline: str
    summary: str
    sources: list[BriefSource]
    published_at: str | None = None
    known_state: str
    watch_condition: str
    major_developments_only: bool
    status: WatchStatus
    latest_change: str | None = None
    last_checked_at: str | None = None
    created_at: str
    updated_at: str
