"""Unattended entrypoint for the Render Cron Job.

Runs one monitor-then-deliver cycle by calling the existing service
functions directly (run_due_watch_checks, deliver_pending_notifications),
never through the HTTP API. This lets monitoring run on its own schedule
independently of whether the free web service is awake.

Monitoring always runs before delivery: a Watch check can create a new
pending notification that should be eligible for delivery in the same
cycle. Each stage isolates its own per-item failures internally (one bad
Watch or one bad email never stops the batch); this module additionally
isolates stage-level failures from each other, so a catastrophic failure
in one stage doesn't prevent the other from running.
"""

import asyncio
import logging
import sys

from ..services.notification_delivery import DeliveryStats, deliver_pending_notifications
from ..services.watch_monitor import MonitorRunStats, run_due_watch_checks

logger = logging.getLogger("run_monitor_cycle")


async def main() -> int:
    monitor_result: MonitorRunStats | None = None
    delivery_result: DeliveryStats | None = None

    try:
        monitor_result = await run_due_watch_checks()
    except Exception as exc:
        logger.error("Monitoring stage failed catastrophically (%s)", type(exc).__name__)

    try:
        delivery_result = await deliver_pending_notifications()
    except Exception as exc:
        logger.error("Delivery stage failed catastrophically (%s)", type(exc).__name__)

    if monitor_result is None and delivery_result is None:
        logger.error("Dispatch monitor cycle did not complete: both stages failed catastrophically")
        return 1

    checked = monitor_result.checked if monitor_result else 0
    new_developments = monitor_result.new_developments if monitor_result else 0
    notifications_created = monitor_result.notifications_created if monitor_result else 0
    monitor_failed = monitor_result.failed if monitor_result else 0

    processed = delivery_result.processed if delivery_result else 0
    sent = delivery_result.sent if delivery_result else 0
    retry_scheduled = delivery_result.retry_scheduled if delivery_result else 0
    delivery_failed = delivery_result.failed if delivery_result else 0

    print("Dispatch monitor cycle complete")
    print(f"Watches checked: {checked}")
    print(f"New developments: {new_developments}")
    print(f"Notifications created: {notifications_created}")
    print(f"Emails processed: {processed}")
    print(f"Emails sent: {sent}")
    print(f"Retries scheduled: {retry_scheduled}")
    print(f"Failures: {monitor_failed + delivery_failed}")

    return 0


def run() -> None:
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
