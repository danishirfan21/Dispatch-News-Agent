"""Controlled (mocked-provider) local verification for the Render Cron Job
entrypoint (app.jobs.run_monitor_cycle.main).

Run with: ./.venv/Scripts/python.exe tests/test_run_monitor_cycle.py

Inserts fixtures directly via a synchronous pymongo client (the job itself
never goes through the FastAPI app, so tests don't either -- this also
sidesteps the motor-client/event-loop binding issue noted in
test_watch_monitor.py) and monkeypatches `search_news_for_query` /
`analyze_watch_update` / `send_email` at their points of use, exactly like
the existing watch_monitor/notification_delivery test suites, so no real
SerpApi/Backboard/Mailjet credits are spent and no real email is sent.
Cleans up every fixture it creates. Requires a running MongoDB (uses
settings.mongodb_uri) and captures stdout to assert no secret/PII leaks.
"""

import asyncio
import io
import sys
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pymongo import MongoClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.jobs import run_monitor_cycle  # noqa: E402
from app.models import Article  # noqa: E402
from app.services import notification_delivery, watch_monitor  # noqa: E402
from app.services.serpapi import SerpApiError  # noqa: E402
from app.services.watch_analysis import WatchAnalysisResult  # noqa: E402

_sync_client = MongoClient(settings.mongodb_uri, tz_aware=True)
_sync_db = _sync_client[settings.mongodb_db_name]

FRESH_ARTICLE = Article(
    id="fresh-1",
    topic="Test Topic",
    title="Something new happened",
    source="Test Wire",
    url="https://example.com/fresh-1",
    published_at="2026-10-04T00:00:00Z",
    snippet="A new development occurred.",
)

RECIPIENT_EMAIL = f"cron-ok-{uuid.uuid4().hex}@example.com"
FAIL_HEADLINE = "FAIL-TRIGGER headline"

_created_user_ids: list = []
_created_watch_ids: list = []


def _insert_user(email: str) -> object:
    now = datetime.now(timezone.utc)
    result = _sync_db.users.insert_one({"email": email, "password_hash": "x", "created_at": now})
    _created_user_ids.append(result.inserted_id)
    return result.inserted_id


def _insert_watch(user_id: object, *, due: bool, story_id: str, headline: str = "Original headline") -> object:
    now = datetime.now(timezone.utc)
    next_check_at = (now - timedelta(minutes=5)) if due else (now + timedelta(hours=1))
    doc = {
        "user_id": str(user_id),
        "story_id": story_id,
        "topic": "Test Topic",
        "headline": headline,
        "summary": "Original known facts about the story.",
        "sources": [{"name": "Wire", "url": "https://example.com/original"}],
        "published_at": "2026-10-01T00:00:00Z",
        "known_state": "Original known facts about the story.",
        "known_state_updated_at": now,
        "watch_condition": "",
        "major_developments_only": True,
        "status": "active",
        "development_status": "no_change",
        "latest_change": None,
        "last_checked_at": None,
        "next_check_at": next_check_at,
        "condition_satisfied_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = _sync_db.watches.insert_one(doc)
    _created_watch_ids.append(result.inserted_id)
    return result.inserted_id


def _cleanup() -> None:
    watch_id_strs = [str(i) for i in _created_watch_ids]
    _sync_db.watch_developments.delete_many({"watch_id": {"$in": watch_id_strs}})
    _sync_db.notifications.delete_many({"watch_id": {"$in": watch_id_strs}})
    _sync_db.watches.delete_many({"_id": {"$in": _created_watch_ids}})
    _sync_db.users.delete_many({"_id": {"$in": _created_user_ids}})


def main_run() -> None:
    try:
        ok_user_id = _insert_user(RECIPIENT_EMAIL)
        fail_user_id = _insert_user(f"cron-fail-{uuid.uuid4().hex}@example.com")
        skip_user_id = _insert_user(f"cron-skip-{uuid.uuid4().hex}@example.com")

        _insert_watch(ok_user_id, due=True, story_id="story-ok")
        _insert_watch(fail_user_id, due=True, story_id="story-fail", headline=FAIL_HEADLINE)
        skip_watch_id = _insert_watch(skip_user_id, due=False, story_id="story-skip")

        async def fake_search(query, topic, limit=None):
            if query == FAIL_HEADLINE:
                raise SerpApiError("Simulated provider failure.")
            return [FRESH_ARTICLE]

        async def fake_analyze(**kwargs):
            return WatchAnalysisResult(
                material_change=True,
                condition_satisfied=False,
                change_summary="A real development happened.",
                new_known_state="Updated via cron cycle test.",
                reason="Official confirmation.",
                supporting_article_ids=["fresh-1"],
            )

        sent_to: list[str] = []

        async def fake_send(*, to_email, subject, text_body, html_body):
            sent_to.append(to_email)
            return "mj-id-test"

        watch_monitor.search_news_for_query = fake_search
        watch_monitor.analyze_watch_update = fake_analyze
        notification_delivery.send_email = fake_send

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = asyncio.run(run_monitor_cycle.main())
        output = buffer.getvalue()
        print(output, end="")

        assert exit_code == 0, f"expected exit code 0, got {exit_code}"

        # 1 due+ok, 1 due+failing, 1 not-due (skipped) -> checked == 2
        assert "Watches checked: 2" in output, output
        assert "New developments: 1" in output, output
        assert "Notifications created: 1" in output, output
        assert "Failures: 1" in output, output
        # Delivery ran in the same cycle and sent the notification monitoring created.
        assert "Emails processed: 1" in output, output
        assert "Emails sent: 1" in output, output
        assert sent_to == [RECIPIENT_EMAIL]
        print("PASS: monitoring-then-delivery ran in one cycle, failure isolated")

        # Nothing sensitive in the printed output.
        lowered = output.lower()
        for secret_marker in (
            settings.monitor_secret,
            settings.mongodb_uri,
            settings.mailjet_api_key,
            settings.mailjet_secret_key,
            RECIPIENT_EMAIL,
            "bearer",
            "mongodb+srv",
        ):
            if secret_marker:
                assert secret_marker.lower() not in lowered, f"leaked marker: {secret_marker!r}"
        print("PASS: no secrets or recipient addresses in job output")

        # The not-due Watch must have been skipped entirely (untouched).
        skip_doc = _sync_db.watches.find_one({"_id": skip_watch_id})
        assert skip_doc["last_checked_at"] is None
        assert skip_doc["development_status"] == "no_change"
        print("PASS: Watch not yet due was skipped")

        print("\n3 assertions blocks passed")
    finally:
        _cleanup()
        remaining_users = _sync_db.users.count_documents({"_id": {"$in": _created_user_ids}})
        remaining_watches = _sync_db.watches.count_documents({"_id": {"$in": _created_watch_ids}})
        assert remaining_users == 0 and remaining_watches == 0
        print("Cleanup verified: 0 fixtures remain")


if __name__ == "__main__":
    main_run()
