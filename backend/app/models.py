from typing import Literal

from pydantic import BaseModel, Field

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
