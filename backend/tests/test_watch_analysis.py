"""Deterministic tests for the Watch material-change analysis service.

Run with: ./.venv/Scripts/python.exe tests/test_watch_analysis.py

No real Backboard/SerpApi calls are made: `send_json_message` is monkeypatched
to return controlled, scripted responses so these are fast and free to run
repeatedly.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Article  # noqa: E402
from app.services import backboard, watch_analysis  # noqa: E402

ARTICLE_REPEAT = Article(
    id="a1",
    topic="Sovereign Debt",
    title="IMF staff-level agreement with Pakistan reported",
    source="Some Outlet",
    url="https://example.com/repeat",
    published_at="2026-10-04T00:00:00Z",
    snippet="The IMF reached a staff-level agreement, as previously reported.",
)

ARTICLE_GENUINE = Article(
    id="a2",
    topic="Sovereign Debt",
    title="IMF Executive Board formally approves $7B facility for Pakistan",
    source="Reuters",
    url="https://example.com/approved",
    published_at="2026-10-04T00:00:00Z",
    snippet="The IMF's Executive Board voted to approve the $7.0B Extended Fund Facility, clearing final disbursement.",
)


async def _run_with_scripted_response(response: dict, articles: list[Article]) -> watch_analysis.WatchAnalysisResult:
    async def fake_send_json_message(system_prompt: str, content: str) -> dict:
        assert "material_change" in system_prompt
        return response

    original = backboard.send_json_message
    watch_analysis.send_json_message = fake_send_json_message
    try:
        return await watch_analysis.analyze_watch_update(
            headline="IMF Executive Board Convenes on $7B Extended Fund Facility",
            topic="Sovereign Debt",
            known_state="Staff-level agreement reached; awaiting Executive Board approval.",
            watch_condition="Notify me when the Executive Board formally signs off on the disbursement.",
            major_developments_only=True,
            last_checked_at=None,
            articles=articles,
        )
    finally:
        watch_analysis.send_json_message = original


async def test_repeated_facts_do_not_trigger_change() -> None:
    result = await _run_with_scripted_response(
        {
            "material_change": False,
            "condition_satisfied": False,
            "change_summary": None,
            "new_known_state": "Staff-level agreement reached; awaiting Executive Board approval.",
            "reason": "Article repeats the already-known staff-level agreement with no new fact.",
            "supporting_article_ids": [],
        },
        [ARTICLE_REPEAT],
    )
    assert result.material_change is False
    assert result.condition_satisfied is False
    assert result.supporting_article_ids == []


async def test_genuine_development_triggers_change() -> None:
    result = await _run_with_scripted_response(
        {
            "material_change": True,
            "condition_satisfied": True,
            "change_summary": "The IMF Executive Board formally approved the $7.0B facility.",
            "new_known_state": "The IMF Executive Board approved the $7.0B Extended Fund Facility; disbursement cleared.",
            "reason": "Executive Board approval is an official decision, satisfying both the major-developments bar and the user's condition.",
            "supporting_article_ids": ["a2"],
        },
        [ARTICLE_GENUINE],
    )
    assert result.material_change is True
    assert result.condition_satisfied is True
    assert result.supporting_article_ids == ["a2"]
    assert "approved" in result.new_known_state.lower()


async def test_material_change_independent_of_condition_satisfied() -> None:
    # Material change happened (negotiations escalated) but the user's specific
    # condition (formal sign-off) is still not met.
    result = await _run_with_scripted_response(
        {
            "material_change": True,
            "condition_satisfied": False,
            "change_summary": "Bilateral financing gap narrowed to $0.5B after new pledges.",
            "new_known_state": "Staff-level agreement reached; bilateral financing gap narrowed to $0.5B; Executive Board approval still pending.",
            "reason": "Meaningful progress occurred, but the Executive Board has not yet voted.",
            "supporting_article_ids": ["a2"],
        },
        [ARTICLE_GENUINE],
    )
    assert result.material_change is True
    assert result.condition_satisfied is False


async def test_malformed_output_raises_watch_analysis_error() -> None:
    try:
        await _run_with_scripted_response(
            {"material_change": True},  # missing required fields
            [ARTICLE_GENUINE],
        )
    except watch_analysis.WatchAnalysisError:
        return
    raise AssertionError("expected WatchAnalysisError for malformed model output")


async def main() -> None:
    tests = [
        test_repeated_facts_do_not_trigger_change,
        test_genuine_development_triggers_change,
        test_material_change_independent_of_condition_satisfied,
        test_malformed_output_raises_watch_analysis_error,
    ]
    for test in tests:
        await test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    asyncio.run(main())
