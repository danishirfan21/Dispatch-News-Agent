"""Controlled (mocked-Mailjet) tests for the notification-delivery worker.

Run with: ./.venv/Scripts/python.exe tests/test_notification_delivery.py

Monkeypatches `send_email` at its point of use in
`app.services.notification_delivery` so no real Mailjet credits are spent
and no real email is sent. Requires a running MongoDB (uses
settings.mongodb_uri).
"""

import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId  # noqa: E402
from pymongo import MongoClient  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.config import settings  # noqa: E402
from app.models import Article  # noqa: E402
from app.services import notification_delivery, watch_monitor  # noqa: E402
from app.services.email import EmailError, build_email_content  # noqa: E402
from app.services.watch_analysis import WatchAnalysisResult  # noqa: E402

_sync_client = MongoClient(settings.mongodb_uri, tz_aware=True)
_sync_db = _sync_client[settings.mongodb_db_name]

AUTH_HEADERS = {"Authorization": f"Bearer {settings.monitor_secret}"}

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


def _create_pending_notification(c: TestClient, *, watch_condition: str = "", condition_satisfied: bool = False) -> dict:
    """Drives a real manual check (mocked SerpApi/Backboard) to produce one
    genuine pending notification tied to real Watch/development documents."""
    watch = _create_watch(c, watch_condition=watch_condition)

    async def fake_search(query, topic, limit=None):
        return [FRESH_ARTICLE]

    async def fake_analyze(**kwargs):
        return WatchAnalysisResult(
            material_change=True,
            condition_satisfied=condition_satisfied,
            change_summary="OpenAI has begun the public rollout of GPT-6 Luna.",
            new_known_state="GPT-6 Luna is rolling out publicly.",
            reason="Official confirmation.",
            supporting_article_ids=["fresh-1"],
        )

    watch_monitor.search_news_for_query = fake_search
    watch_monitor.analyze_watch_update = fake_analyze
    resp = c.post(f"/api/watches/{watch['id']}/check")
    assert resp.status_code == 200, resp.text

    notification = _sync_db.notifications.find_one({"watch_id": watch["id"]})
    assert notification is not None, "expected a pending notification to have been created"
    return notification


# ---------------------------------------------------------------------------
# Unit tests: deterministic email content (no DB, no app)
# ---------------------------------------------------------------------------


def test_condition_met_email_mentions_condition() -> None:
    subject, text_body, html_body = build_email_content(
        watch_headline="Regulators review the proposed TechCorp merger",
        development_summary="Regulators officially approved the merger.",
        watch_condition="Notify me when the merger is officially approved.",
        condition_satisfied=True,
        sources=[{"name": "Test Wire", "url": "https://example.com/fresh-1"}],
    )
    assert subject == "Dispatch: Your watch condition was met"
    assert "YOUR WATCH CONDITION WAS MET" in text_body
    assert "Notify me when the merger is officially approved." in text_body
    assert "Your watch condition was met" in html_body or "condition was met" in html_body.lower()
    print("PASS test_condition_met_email_mentions_condition")


def test_no_condition_email_does_not_claim_condition_met(client: TestClient = None) -> None:
    subject, text_body, html_body = build_email_content(
        watch_headline="Regulators review the proposed TechCorp merger",
        development_summary="Regulators opened a review of the proposed merger.",
        watch_condition="",
        condition_satisfied=False,
        sources=[{"name": "Test Wire", "url": "https://example.com/fresh-0"}],
    )
    assert subject.startswith("Dispatch: New development")
    assert "CONDITION WAS MET" not in text_body
    assert "condition was met" not in html_body.lower()
    print("PASS test_no_condition_email_does_not_claim_condition_met")


def test_text_email_includes_source_urls() -> None:
    _, text_body, _ = build_email_content(
        watch_headline="Headline",
        development_summary="Summary.",
        watch_condition="",
        condition_satisfied=False,
        sources=[{"name": "Test Wire", "url": "https://example.com/fresh-1"}],
    )
    assert "https://example.com/fresh-1" in text_body
    assert "Test Wire" in text_body
    print("PASS test_text_email_includes_source_urls")


def test_html_email_contains_safe_clickable_source_link() -> None:
    _, _, html_body = build_email_content(
        watch_headline="Headline",
        development_summary="Summary.",
        watch_condition="",
        condition_satisfied=False,
        sources=[{"name": "Test <Wire>", "url": "https://example.com/fresh-1?x=1&y=2"}],
    )
    assert '<a href="https://example.com/fresh-1?x=1&amp;y=2"' in html_body
    assert "Test &lt;Wire&gt;" in html_body
    print("PASS test_html_email_contains_safe_clickable_source_link")


# ---------------------------------------------------------------------------
# Integration tests: real Watch/development/notification docs, mocked send
# ---------------------------------------------------------------------------


def test_successful_send_marks_sent_with_message_id(client: TestClient) -> None:
    c = _register_and_login(client, f"nd-sent-{uuid.uuid4().hex}@example.com")
    notification = _create_pending_notification(c)

    async def fake_send(*, to_email, subject, text_body, html_body):
        return "mj-message-id-123"

    notification_delivery.send_email = fake_send
    resp = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    stats = resp.json()
    assert stats["processed"] >= 1
    assert stats["sent"] >= 1

    updated = _sync_db.notifications.find_one({"_id": notification["_id"]})
    assert updated["status"] == "sent"
    assert updated["sent_at"] is not None
    assert updated["provider_message_id"] == "mj-message-id-123"
    print("PASS test_successful_send_marks_sent_with_message_id")

    # Re-running delivery must not re-send an already-sent notification.
    resp2 = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
    assert resp2.status_code == 200, resp2.text
    again = _sync_db.notifications.find_one({"_id": notification["_id"]})
    assert again["sent_at"] == updated["sent_at"]
    print("PASS test_rerun_does_not_resend_already_sent_notification")


def test_message_id_omitted_when_provider_gives_none(client: TestClient) -> None:
    c = _register_and_login(client, f"nd-noid-{uuid.uuid4().hex}@example.com")
    notification = _create_pending_notification(c)

    async def fake_send(*, to_email, subject, text_body, html_body):
        return None

    notification_delivery.send_email = fake_send
    resp = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text

    updated = _sync_db.notifications.find_one({"_id": notification["_id"]})
    assert updated["status"] == "sent"
    assert "provider_message_id" not in updated
    print("PASS test_message_id_omitted_when_provider_gives_none")


def test_recipient_resolved_server_side_from_user_id(client: TestClient) -> None:
    email = f"nd-recipient-{uuid.uuid4().hex}@example.com"
    c = _register_and_login(client, email)
    _create_pending_notification(c)

    captured = {}

    async def fake_send(*, to_email, subject, text_body, html_body):
        captured["to_email"] = to_email
        return "mj-id"

    notification_delivery.send_email = fake_send
    resp = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    assert captured["to_email"] == email
    print("PASS test_recipient_resolved_server_side_from_user_id")


def test_missing_user_fails_safely(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": str(ObjectId()),  # no such user
        "watch_id": str(ObjectId()),
        "development_id": str(ObjectId()),
        "type": "watch_development",
        "title": "New development: Ghost story",
        "body": "Something happened.",
        "sources": [],
        "status": "pending",
        "attempt_count": 0,
        "last_attempt_at": None,
        "next_attempt_at": now,
        "last_error_code": None,
        "created_at": now,
        "sent_at": None,
        "failed_at": None,
    }
    inserted_id = _sync_db.notifications.insert_one(doc).inserted_id

    async def fake_send(*, to_email, subject, text_body, html_body):
        raise AssertionError("send_email should never be called for a missing user")

    notification_delivery.send_email = fake_send
    resp = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text

    updated = _sync_db.notifications.find_one({"_id": inserted_id})
    assert updated["status"] == "failed"
    assert updated["last_error_code"] == "missing_user"
    print("PASS test_missing_user_fails_safely")


def test_temporary_failure_schedules_retry_with_incrementing_attempt_count(client: TestClient) -> None:
    c = _register_and_login(client, f"nd-retry-{uuid.uuid4().hex}@example.com")
    notification = _create_pending_notification(c)

    async def failing_send(*, to_email, subject, text_body, html_body):
        raise EmailError("Simulated network failure.", category="network_error", retryable=True)

    notification_delivery.send_email = failing_send
    resp = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    stats = resp.json()
    assert stats["retry_scheduled"] >= 1

    updated = _sync_db.notifications.find_one({"_id": notification["_id"]})
    assert updated["status"] == "pending"
    assert updated["attempt_count"] == 1
    assert updated["next_attempt_at"] > datetime.now(timezone.utc)
    assert updated["last_error_code"] == "network_error"
    print("PASS test_temporary_failure_schedules_retry_with_incrementing_attempt_count")

    # Not yet due — a second run right away must not touch it again.
    resp2 = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
    assert resp2.status_code == 200, resp2.text
    unchanged = _sync_db.notifications.find_one({"_id": notification["_id"]})
    assert unchanged["attempt_count"] == 1
    print("PASS test_not_yet_due_retry_is_skipped")


def test_max_attempts_produces_terminal_failed_state(client: TestClient) -> None:
    c = _register_and_login(client, f"nd-maxfail-{uuid.uuid4().hex}@example.com")
    notification = _create_pending_notification(c)

    async def failing_send(*, to_email, subject, text_body, html_body):
        raise EmailError("Simulated network failure.", category="network_error", retryable=True)

    notification_delivery.send_email = failing_send

    for attempt in range(1, 4):
        _sync_db.notifications.update_one(
            {"_id": notification["_id"]},
            {"$set": {"next_attempt_at": datetime.now(timezone.utc) - timedelta(seconds=1)}},
        )
        resp = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
        assert resp.status_code == 200, resp.text
        updated = _sync_db.notifications.find_one({"_id": notification["_id"]})
        assert updated["attempt_count"] == attempt, f"expected attempt_count={attempt}, got {updated['attempt_count']}"

    final = _sync_db.notifications.find_one({"_id": notification["_id"]})
    assert final["status"] == "failed"
    assert final["failed_at"] is not None
    print("PASS test_max_attempts_produces_terminal_failed_state")


def test_one_failed_notification_does_not_block_others(client: TestClient) -> None:
    c1 = _register_and_login(client, f"nd-ok-{uuid.uuid4().hex}@example.com")
    good_notification = _create_pending_notification(c1)

    now = datetime.now(timezone.utc)
    bad_doc = {
        "user_id": str(ObjectId()),
        "watch_id": str(ObjectId()),
        "development_id": str(ObjectId()),
        "type": "watch_development",
        "title": "New development: Ghost story",
        "body": "Something happened.",
        "sources": [],
        "status": "pending",
        "attempt_count": 0,
        "last_attempt_at": None,
        "next_attempt_at": now - timedelta(seconds=1),
        "last_error_code": None,
        "created_at": now,
        "sent_at": None,
        "failed_at": None,
    }
    _sync_db.notifications.insert_one(bad_doc)

    async def fake_send(*, to_email, subject, text_body, html_body):
        return "mj-id-ok"

    notification_delivery.send_email = fake_send
    resp = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    stats = resp.json()
    assert stats["sent"] >= 1
    assert stats["failed"] >= 1

    updated_good = _sync_db.notifications.find_one({"_id": good_notification["_id"]})
    assert updated_good["status"] == "sent"
    print("PASS test_one_failed_notification_does_not_block_others")


def test_two_concurrent_delivery_runs_cannot_both_send_same_notification(client: TestClient) -> None:
    c = _register_and_login(client, f"nd-concurrent-{uuid.uuid4().hex}@example.com")
    notification = _create_pending_notification(c)

    send_calls = []

    async def slow_send(*, to_email, subject, text_body, html_body):
        import asyncio

        await asyncio.sleep(0.3)
        send_calls.append(1)
        return "mj-id-race"

    notification_delivery.send_email = slow_send

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(client.post, "/api/internal/notifications/deliver", headers=AUTH_HEADERS)
            for _ in range(2)
        ]
        responses = [f.result() for f in futures]

    for resp in responses:
        assert resp.status_code == 200, resp.text

    assert len(send_calls) == 1, f"expected exactly one real send, got {len(send_calls)}"
    updated = _sync_db.notifications.find_one({"_id": notification["_id"]})
    assert updated["status"] == "sent"
    print("PASS test_two_concurrent_delivery_runs_cannot_both_send_same_notification")


def test_internal_delivery_endpoint_rejects_missing_or_wrong_secret(client: TestClient) -> None:
    resp = client.post("/api/internal/notifications/deliver")
    assert resp.status_code == 401

    resp = client.post(
        "/api/internal/notifications/deliver", headers={"Authorization": "Bearer definitely-not-the-secret"}
    )
    assert resp.status_code == 401
    print("PASS test_internal_delivery_endpoint_rejects_missing_or_wrong_secret")


def test_valid_secret_runs_delivery_worker(client: TestClient) -> None:
    c = _register_and_login(client, f"nd-valid-{uuid.uuid4().hex}@example.com")
    _create_pending_notification(c)

    async def fake_send(*, to_email, subject, text_body, html_body):
        return "mj-id-valid"

    notification_delivery.send_email = fake_send
    resp = client.post("/api/internal/notifications/deliver", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    stats = resp.json()
    assert set(stats.keys()) == {"processed", "sent", "retry_scheduled", "failed"}
    assert stats["sent"] >= 1
    print("PASS test_valid_secret_runs_delivery_worker")


def main_run() -> None:
    unit_tests = [
        test_condition_met_email_mentions_condition,
        test_no_condition_email_does_not_claim_condition_met,
        test_text_email_includes_source_urls,
        test_html_email_contains_safe_clickable_source_link,
    ]
    for test in unit_tests:
        test()

    integration_tests = [
        test_successful_send_marks_sent_with_message_id,
        test_message_id_omitted_when_provider_gives_none,
        test_recipient_resolved_server_side_from_user_id,
        test_missing_user_fails_safely,
        test_temporary_failure_schedules_retry_with_incrementing_attempt_count,
        test_max_attempts_produces_terminal_failed_state,
        test_one_failed_notification_does_not_block_others,
        test_two_concurrent_delivery_runs_cannot_both_send_same_notification,
        test_internal_delivery_endpoint_rejects_missing_or_wrong_secret,
        test_valid_secret_runs_delivery_worker,
    ]
    with TestClient(main.app) as client:
        for test in integration_tests:
            test(client)

    print(f"\n{len(unit_tests) + len(integration_tests)} test functions passed")


if __name__ == "__main__":
    main_run()
