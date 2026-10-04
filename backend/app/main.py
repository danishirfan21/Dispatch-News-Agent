from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import (
    NewsSearchRequest,
    NewsSearchResponse,
    ParseInterestsRequest,
    ParseInterestsResponse,
)
from .services.backboard import BackboardError, parse_interests
from .services.serpapi import SerpApiError, search_news

app = FastAPI(title="Dispatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
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
