"""Controlled (mocked-evidence) tests for Step 9: development history, the
notification outbox, duplicate-development protection, the condition
notification policy, and the automatic monitor.

Run with: ./.venv/Scripts/python.exe tests/test_watch_monitor.py

Monkeypatches `search_news_for_query` and `analyze_watch_update` at their
point of use in `app.services.watch_monitor` so no real SerpApi/Backboard
credits are spent. Requires a running MongoDB (uses settings.mongodb_uri).
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId  # noqa: E402
from pymongo import MongoClient  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.config import settings  # noqa: E402
from app.models import Article  # noqa: E402
from app.services import watch_monitor  # noqa: E402
from app.services.watch_analysis import WatchAnalysisResult  # noqa: E402

# A separate SYNCHRONOUS client for test assertions only. The app's own
# motor (async) client is bound to the TestClient's event loop, so mixing it
# with asyncio.run() here would create a second, conflicting event loop.
_sync_client = MongoClient(settings.mongodb_uri, tz_aware=True)
_sync_db = _sync_client[settings.mongodb_db_name]


def get_db():
    return _sync_db

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


def _create_watch(c: TestClient, *, watch_condition: str = "") -> dict:
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
    watch = resp.json()

    if watch_condition:
        resp = c.patch(f"/api/watches/{watch['id']}", json={"watch_condition": watch_condition})
        assert resp.status_code == 200, resp.text
        watch = resp.json()

    return watch


def _material_change_analysis(
    *, change_summary: str, condition_satisfied: bool, new_known_state: str, supporting_ids: list[str]
) -> WatchAnalysisResult:
    return WatchAnalysisResult(
        material_change=True,
        condition_satisfied=condition_satisfied,
        change_summary=change_summary,
        new_known_state=new_known_state,
        reason="Official confirmation.",
        supporting_article_ids=supporting_ids,
    )


def test_material_change_creates_one_development_and_notification(client: TestClient) -> None:
    c = _register_and_login(client, f"wm-dev-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return _material_change_analysis(
            change_summary="OpenAI has begun the public rollout of GPT-6 Luna.",
            condition_satisfied=False,
            new_known_state="GPT-6 Luna is rolling out publicly.",
            supporting_ids=["fresh-1"],
        )

    watch_monitor.search_news_for_query = fake_search
    watch_monitor.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text

    resp = c.get(f"/api/watches/{watch['id']}/developments")
    assert resp.status_code == 200, resp.text
    developments = resp.json()["developments"]
    assert len(developments) == 1
    assert developments[0]["summary"] == "OpenAI has begun the public rollout of GPT-6 Luna."
    assert developments[0]["known_state_before"] == "Original known facts about the story."
    assert developments[0]["known_state_after"] == "GPT-6 Luna is rolling out publicly."
    assert developments[0]["trigger"] == "manual"
    assert len(developments[0]["sources"]) == 1

    db = get_db()
    notification = db.notifications.find_one({"development_id": developments[0]["id"]})
    assert notification is not None
    assert notification["status"] == "pending"
    assert notification["type"] == "watch_development"
    assert "GPT-6" in notification["title"] or "GPT-6" in notification["body"]
    print("PASS test_material_change_creates_one_development_and_notification")


def test_no_change_creates_no_development_or_notification(client: TestClient) -> None:
    c = _register_and_login(client, f"wm-nochange-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return WatchAnalysisResult(
            material_change=False,
            condition_satisfied=False,
            change_summary=None,
            new_known_state=watch["known_state"],
            reason="Repeats known facts.",
            supporting_article_ids=[],
        )

    watch_monitor.search_news_for_query = fake_search
    watch_monitor.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text

    resp = c.get(f"/api/watches/{watch['id']}/developments")
    assert resp.status_code == 200, resp.text
    assert resp.json()["developments"] == []
    print("PASS test_no_change_creates_no_development_or_notification")


def test_duplicate_development_guard_blocks_repeat(client: TestClient) -> None:
    c = _register_and_login(client, f"wm-dup-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze_first(**kwargs):
        return _material_change_analysis(
            change_summary="The company announced a major leadership change today.",
            condition_satisfied=False,
            new_known_state="New CEO appointed.",
            supporting_ids=["fresh-1"],
        )

    watch_monitor.search_news_for_query = fake_search
    watch_monitor.analyze_watch_update = fake_analyze_first
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text
    assert resp.json()["check"]["material_change"] is True

    # A second, independent outlet rewords the same real-world fact. Even
    # though known_state changed, the model (incorrectly) still flags this as
    # material_change=True with a near-identical summary — the deterministic
    # similarity guard must catch it since known_state alone didn't prevent it.
    async def fake_analyze_repeat(**kwargs):
        return _material_change_analysis(
            change_summary="The company announced a major leadership change today, per sources.",
            condition_satisfied=False,
            new_known_state="New CEO appointed (confirmed again).",
            supporting_ids=["fresh-1"],
        )

    watch_monitor.analyze_watch_update = fake_analyze_repeat
    resp2 = c.post(f"/api/watches/{watch['id']}/check")
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["check"]["material_change"] is False

    resp = c.get(f"/api/watches/{watch['id']}/developments")
    developments = resp.json()["developments"]
    assert len(developments) == 1, f"expected exactly one development, got {len(developments)}"
    print("PASS test_duplicate_development_guard_blocks_repeat")


def test_custom_condition_false_records_development_without_notification(client: TestClient) -> None:
    c = _register_and_login(client, f"wm-condfalse-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c, watch_condition="Notify me when the merger is officially approved.")

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return _material_change_analysis(
            change_summary="Regulators opened a review of the proposed merger.",
            condition_satisfied=False,
            new_known_state="Merger under regulatory review.",
            supporting_ids=["fresh-1"],
        )

    watch_monitor.search_news_for_query = fake_search
    watch_monitor.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text
    assert resp.json()["check"]["material_change"] is True
    assert resp.json()["check"]["condition_satisfied"] is False

    resp = c.get(f"/api/watches/{watch['id']}/developments")
    developments = resp.json()["developments"]
    assert len(developments) == 1

    db = get_db()
    notification = db.notifications.find_one({"development_id": developments[0]["id"]})
    assert notification is None
    print("PASS test_custom_condition_false_records_development_without_notification")


def test_custom_condition_true_notifies_once_then_suppresses_repeats(client: TestClient) -> None:
    c = _register_and_login(client, f"wm-condtrue-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c, watch_condition="Notify me when the merger is officially approved.")

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze_approved(**kwargs):
        return _material_change_analysis(
            change_summary="Regulators officially approved the merger.",
            condition_satisfied=True,
            new_known_state="Merger approved.",
            supporting_ids=["fresh-1"],
        )

    watch_monitor.search_news_for_query = fake_search
    watch_monitor.analyze_watch_update = fake_analyze_approved
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text
    assert resp.json()["check"]["condition_satisfied"] is True

    resp = c.get(f"/api/watches/{watch['id']}/developments")
    first_development_id = resp.json()["developments"][0]["id"]

    db = get_db()
    notification = db.notifications.find_one({"development_id": first_development_id})
    assert notification is not None

    # A later check confirms the condition remains satisfied with a distinct
    # new fact (so it's not blocked by the duplicate-development guard) — the
    # notification policy itself (condition_satisfied_at already set) must
    # suppress a second notification.
    async def fake_analyze_still_satisfied(**kwargs):
        return _material_change_analysis(
            change_summary="Shareholders ratified the already-approved merger terms.",
            condition_satisfied=True,
            new_known_state="Merger approved and ratified.",
            supporting_ids=["fresh-1"],
        )

    watch_monitor.analyze_watch_update = fake_analyze_still_satisfied
    resp2 = c.post(f"/api/watches/{watch['id']}/check")
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["check"]["material_change"] is True

    resp = c.get(f"/api/watches/{watch['id']}/developments")
    developments = resp.json()["developments"]
    assert len(developments) == 2, "the second genuine fact should still be recorded as history"

    second_development_id = developments[0]["id"]
    assert second_development_id != first_development_id
    notification_count = db.notifications.count_documents({"watch_id": watch["id"]})
    assert notification_count == 1, "condition already satisfied once must not notify again"
    print("PASS test_custom_condition_true_notifies_once_then_suppresses_repeats")


def test_editing_watch_condition_resets_satisfaction_state(client: TestClient) -> None:
    c = _register_and_login(client, f"wm-reset-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c, watch_condition="Notify me when X happens.")

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return _material_change_analysis(
            change_summary="X happened.",
            condition_satisfied=True,
            new_known_state="X has happened.",
            supporting_ids=["fresh-1"],
        )

    watch_monitor.search_news_for_query = fake_search
    watch_monitor.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text

    resp = c.patch(f"/api/watches/{watch['id']}", json={"watch_condition": "Notify me when Y happens."})
    assert resp.status_code == 200, resp.text

    db = get_db()
    doc = db.watches.find_one({"_id": ObjectId(watch["id"])})
    assert doc["condition_satisfied_at"] is None
    print("PASS test_editing_watch_condition_resets_satisfaction_state")


def test_user_cannot_read_another_users_development_history(client: TestClient) -> None:
    c = _register_and_login(client, f"wm-owner-a-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return _material_change_analysis(
            change_summary="Something happened.",
            condition_satisfied=False,
            new_known_state="Updated.",
            supporting_ids=["fresh-1"],
        )

    watch_monitor.search_news_for_query = fake_search
    watch_monitor.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text

    _register_and_login(client, f"wm-owner-b-{uuid.uuid4().hex}@example.com")
    resp = client.get(f"/api/watches/{watch['id']}/developments")
    assert resp.status_code == 404
    print("PASS test_user_cannot_read_another_users_development_history")


def test_internal_monitor_endpoint_rejects_missing_or_wrong_secret(client: TestClient) -> None:
    resp = client.post("/api/internal/monitor/run")
    assert resp.status_code == 401

    resp = client.post(
        "/api/internal/monitor/run", headers={"Authorization": "Bearer definitely-not-the-secret"}
    )
    assert resp.status_code == 401
    print("PASS test_internal_monitor_endpoint_rejects_missing_or_wrong_secret")


def test_internal_monitor_endpoint_runs_due_watches(client: TestClient) -> None:

    c = _register_and_login(client, f"wm-auto-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)

    db = get_db()
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.watches.update_one(
            {"_id": ObjectId(watch["id"])}, {"$set": {"next_check_at": past}}
        )

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return _material_change_analysis(
            change_summary="Automatic check found a real development.",
            condition_satisfied=False,
            new_known_state="Updated via automatic check.",
            supporting_ids=["fresh-1"],
        )

    watch_monitor.search_news_for_query = fake_search
    watch_monitor.analyze_watch_update = fake_analyze

    resp = client.post(
        "/api/internal/monitor/run", headers={"Authorization": f"Bearer {settings.monitor_secret}"}
    )
    assert resp.status_code == 200, resp.text
    stats = resp.json()
    assert stats["checked"] >= 1
    assert stats["new_developments"] >= 1
    assert stats["notifications_created"] >= 1
    assert "raw" not in str(stats).lower()

    updated_doc = db.watches.find_one({"_id": ObjectId(watch["id"])})
    assert updated_doc["next_check_at"] > past
    print("PASS test_internal_monitor_endpoint_runs_due_watches")


def test_paused_watch_excluded_from_due_query(client: TestClient) -> None:
    c = _register_and_login(client, f"wm-paused-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)

    resp = c.patch(f"/api/watches/{watch['id']}", json={"status": "paused"})
    assert resp.status_code == 200, resp.text

    db = get_db()
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.watches.update_one(
            {"_id": ObjectId(watch["id"])}, {"$set": {"next_check_at": past}}
        )

    # Mirrors repositories.find_due_watches' filter exactly; run with the
    # synchronous client since this test doesn't need the app's event loop.
    due = list(db.watches.find({"status": "active", "next_check_at": {"$lte": datetime.now(timezone.utc)}}))
    assert all(str(d["_id"]) != watch["id"] for d in due)
    print("PASS test_paused_watch_excluded_from_due_query")


def test_failed_automatic_check_preserves_state_and_continues(client: TestClient) -> None:

    c = _register_and_login(client, f"wm-fail-{uuid.uuid4().hex}@example.com")
    watch = _create_watch(c)
    original_known_state = watch["known_state"]

    db = get_db()
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.watches.update_one(
            {"_id": ObjectId(watch["id"])}, {"$set": {"next_check_at": past}}
        )

    from app.services.serpapi import SerpApiError

    async def failing_search(query, topic, limit=None):
        raise SerpApiError("Simulated provider failure.")

    watch_monitor.search_news_for_query = failing_search

    # Drive run_due_watch_checks() through the HTTP endpoint so it executes
    # in the same event loop as the app's motor client.
    resp = client.post(
        "/api/internal/monitor/run", headers={"Authorization": f"Bearer {settings.monitor_secret}"}
    )
    assert resp.status_code == 200, resp.text
    stats = resp.json()
    assert stats["failed"] >= 1
    assert stats["new_developments"] == 0

    updated_doc = db.watches.find_one({"_id": ObjectId(watch["id"])})
    assert updated_doc["known_state"] == original_known_state
    assert updated_doc["latest_change"] is None
    assert updated_doc["next_check_at"] > past

    resp = c.get(f"/api/watches/{watch['id']}/developments")
    assert resp.json()["developments"] == []

    notification_count = db.notifications.count_documents({"watch_id": watch["id"]})
    assert notification_count == 0
    print("PASS test_failed_automatic_check_preserves_state_and_continues")


def main_run() -> None:
    tests = [
        test_material_change_creates_one_development_and_notification,
        test_no_change_creates_no_development_or_notification,
        test_duplicate_development_guard_blocks_repeat,
        test_custom_condition_false_records_development_without_notification,
        test_custom_condition_true_notifies_once_then_suppresses_repeats,
        test_editing_watch_condition_resets_satisfaction_state,
        test_user_cannot_read_another_users_development_history,
        test_internal_monitor_endpoint_rejects_missing_or_wrong_secret,
        test_internal_monitor_endpoint_runs_due_watches,
        test_paused_watch_excluded_from_due_query,
        test_failed_automatic_check_preserves_state_and_continues,
    ]
    with TestClient(main.app) as client:
        for test in tests:
            test(client)
    print(f"\n{len(tests)} test functions passed")


if __name__ == "__main__":
    main_run()
