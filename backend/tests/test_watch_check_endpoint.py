"""Controlled (mocked-evidence) tests for the POST /api/watches/{id}/check endpoint.

Run with: ./.venv/Scripts/python.exe tests/test_watch_check_endpoint.py

Uses starlette's TestClient against the real app, but monkeypatches
`search_news_for_query` and `analyze_watch_update` at their point of use in
`app.main` so no real SerpApi or Backboard credits are spent. Requires a
running MongoDB (uses the same settings.mongodb_uri as the real app) since
repositories are exercised for real.
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.models import Article  # noqa: E402
from app.services.watch_analysis import WatchAnalysisResult  # noqa: E402

FRESH_ARTICLE = Article(
    id="fresh-1",
    topic="Test Topic",
    title="Something new happened",
    source="Test Wire",
    url="https://example.com/fresh-1",
    published_at="2026-10-04T00:00:00Z",
    snippet="A new development occurred.",
)


def _register_and_login(client: TestClient, email: str) -> TestClient:
    client.cookies.clear()
    resp = client.post("/api/auth/register", json={"email": email, "password": "TestPass123!"})
    assert resp.status_code == 200, resp.text
    return client


def _create_watch(c: TestClient) -> dict:
    # Seed a brief so a story_id exists to follow.
    async def fake_generate_brief(interest_profile, articles):
        from app.models import BriefStory

        return [
            BriefStory(
                id="story-1",
                topic="Test Topic",
                headline="Original headline",
                summary="Original known facts about the story.",
                why_this_matters_to_you="Because testing.",
                source_article_ids=["a1"],
                sources=[{"name": "Wire", "url": "https://example.com/original"}],
                published_at="2026-10-01T00:00:00Z",
                importance="medium",
            )
        ]

    original_generate_brief = main.generate_brief
    main.generate_brief = fake_generate_brief
    try:
        resp = c.post(
            "/api/brief/generate",
            json={
                "interest_profile": {"interests": [], "excluded_topics": []},
                "articles": [
                    {
                        "id": "a1",
                        "topic": "Test Topic",
                        "title": "Original headline",
                        "source": "Wire",
                        "url": "https://example.com/original",
                        "published_at": "2026-10-01T00:00:00Z",
                        "snippet": None,
                    }
                ],
            },
        )
        assert resp.status_code == 200, resp.text
    finally:
        main.generate_brief = original_generate_brief

    resp = c.post("/api/watches", json={"story_id": "story-1"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_no_change_does_not_mutate_known_state(client: TestClient) -> None:
    c = _register_and_login(client, f"watch-nochange-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)
    original_known_state = watch["known_state"]

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return WatchAnalysisResult(
            material_change=False,
            condition_satisfied=False,
            change_summary=None,
            new_known_state=original_known_state,
            reason="Repeats known facts.",
            supporting_article_ids=[],
        )

    main.search_news_for_query = fake_search
    main.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["check"]["material_change"] is False
    assert body["watch"]["development_status"] == "no_change"
    assert body["watch"]["known_state"] == original_known_state
    assert body["watch"]["latest_change"] is None
    assert body["watch"]["last_checked_at"] is not None
    print("PASS test_no_change_does_not_mutate_known_state")


def test_meaningful_change_persists_new_state_and_sources(client: TestClient) -> None:
    c = _register_and_login(client, f"watch-change-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return WatchAnalysisResult(
            material_change=True,
            condition_satisfied=True,
            change_summary="A genuinely new development occurred.",
            new_known_state="Updated known state reflecting the new development.",
            reason="Official confirmation.",
            supporting_article_ids=["fresh-1"],
        )

    main.search_news_for_query = fake_search
    main.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["check"]["material_change"] is True
    assert body["check"]["condition_satisfied"] is True
    assert body["watch"]["development_status"] == "new_development"
    assert body["watch"]["known_state"] == "Updated known state reflecting the new development."
    assert body["watch"]["latest_change"]["summary"] == "A genuinely new development occurred."
    assert len(body["watch"]["latest_change"]["sources"]) == 1
    assert body["watch"]["latest_change"]["sources"][0]["url"] == "https://example.com/fresh-1"
    print("PASS test_meaningful_change_persists_new_state_and_sources")

    # Subsequent no-change check should revert development_status, per item 18.
    async def fake_analyze_followup(**kwargs):
        return WatchAnalysisResult(
            material_change=False,
            condition_satisfied=False,
            change_summary=None,
            new_known_state=body["watch"]["known_state"],
            reason="No further change.",
            supporting_article_ids=[],
        )

    main.analyze_watch_update = fake_analyze_followup
    resp2 = c.post(f"/api/watches/{watch['id']}/check")
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    assert body2["watch"]["development_status"] == "no_change"
    assert body2["watch"]["known_state"] == body["watch"]["known_state"]
    print("PASS test_subsequent_no_change_reverts_development_status")


def test_unverified_material_change_claim_is_downgraded(client: TestClient) -> None:
    """Model claims material_change=True but cites no real supporting article ids.

    The endpoint's conservative verification gate must downgrade this to a
    no-change outcome rather than trusting the claim at face value.
    """
    c = _register_and_login(client, f"watch-unverified-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)
    original_known_state = watch["known_state"]

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return WatchAnalysisResult(
            material_change=True,
            condition_satisfied=True,
            change_summary="Claims a change but cites nothing real.",
            new_known_state="Should never be persisted.",
            reason="Hallucinated.",
            supporting_article_ids=["does-not-exist"],
        )

    main.search_news_for_query = fake_search
    main.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["check"]["material_change"] is False
    assert body["watch"]["development_status"] == "no_change"
    assert body["watch"]["known_state"] == original_known_state
    print("PASS test_unverified_material_change_claim_is_downgraded")


def test_zero_fresh_articles_short_circuits_without_model_call(client: TestClient) -> None:
    c = _register_and_login(client, f"watch-zero-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)

    async def fake_search(query, topic, limit=None):
        return []

    called = {"value": False}

    async def fake_analyze(**kwargs):
        called["value"] = True
        raise AssertionError("analyze_watch_update should not be called with zero fresh articles")

    main.search_news_for_query = fake_search
    main.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["watch"]["development_status"] == "no_change"
    assert called["value"] is False
    print("PASS test_zero_fresh_articles_short_circuits_without_model_call")


def main_run() -> None:
    tests = [
        test_no_change_does_not_mutate_known_state,
        test_meaningful_change_persists_new_state_and_sources,
        test_unverified_material_change_claim_is_downgraded,
        test_zero_fresh_articles_short_circuits_without_model_call,
    ]
    with TestClient(main.app) as client:
        for test in tests:
            test(client)
    print(f"\n{len(tests)} test functions passed")


if __name__ == "__main__":
    main_run()
