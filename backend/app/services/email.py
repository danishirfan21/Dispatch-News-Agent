"""Mailjet email delivery for the notification outbox.

Deliberately dumb: builds deterministic email copy from already-persisted
notification/Watch/development data (never an LLM call) and sends it through
Mailjet's v3.1 Send API over plain httpx. Never logs or raises anything that
contains Mailjet credentials, the raw provider response body, or (per the
existing logging policy) the recipient's email address.
"""

import html
import logging

import httpx

from ..config import settings

logger = logging.getLogger("email")

MAILJET_SEND_URL = "https://api.mailjet.com/v3.1/send"


class EmailError(Exception):
    """Raised for any email-delivery failure. Message is safe to log.

    `category` is a short, safe operational tag (never provider internals)
    used to decide retry behavior and to record as last_error_code.
    `retryable` tells the delivery worker whether a future attempt is worth
    scheduling at all.
    """

    def __init__(self, message: str, *, category: str, retryable: bool) -> None:
        super().__init__(message)
        self.category = category
        self.retryable = retryable


async def send_email(*, to_email: str, subject: str, text_body: str, html_body: str) -> str | None:
    """Sends one email via Mailjet. Returns a provider message id if one was
    present in the response, else None. Raises EmailError on any failure."""
    if not settings.mailjet_api_key or not settings.mailjet_secret_key or not settings.mail_from_email:
        logger.error("Email delivery skipped: Mailjet is not configured")
        raise EmailError(
            "Email delivery isn't configured on the server yet.", category="not_configured", retryable=False
        )

    payload = {
        "Messages": [
            {
                "From": {"Email": settings.mail_from_email, "Name": settings.mail_from_name},
                "To": [{"Email": to_email}],
                "Subject": subject,
                "TextPart": text_body,
                "HTMLPart": html_body,
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            response = await client.post(
                MAILJET_SEND_URL,
                json=payload,
                auth=(settings.mailjet_api_key, settings.mailjet_secret_key),
            )
    except httpx.TimeoutException as exc:
        logger.warning("Mailjet request timed out: %s", type(exc).__name__)
        raise EmailError("The email service took too long to respond.", category="timeout", retryable=True) from exc
    except httpx.RequestError as exc:
        logger.warning("Mailjet request failed: %s", type(exc).__name__)
        raise EmailError("Couldn't reach the email service.", category="network_error", retryable=True) from exc

    if response.status_code == 429:
        logger.warning("Mailjet rate limit exceeded")
        raise EmailError(
            "The email service is temporarily rate-limited.", category="provider_429", retryable=True
        )

    if 500 <= response.status_code < 600:
        logger.warning("Mailjet returned a server error status=%s", response.status_code)
        raise EmailError("The email service returned a server error.", category="provider_5xx", retryable=True)

    if 400 <= response.status_code < 500:
        logger.warning("Mailjet rejected the request status=%s", response.status_code)
        raise EmailError("The email service rejected the request.", category="provider_4xx", retryable=False)

    try:
        body = response.json()
        first_message = body["Messages"][0]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("Mailjet response did not match the expected shape: %s", type(exc).__name__)
        raise EmailError(
            "The email service sent back something we couldn't read.", category="malformed_response", retryable=False
        ) from exc

    if first_message.get("Status") != "success":
        logger.warning("Mailjet reported a non-success send status")
        raise EmailError("The email service reported the send failed.", category="provider_4xx", retryable=False)

    message_id = None
    to_list = first_message.get("To") or []
    if to_list and isinstance(to_list[0], dict) and to_list[0].get("MessageID"):
        message_id = str(to_list[0]["MessageID"])

    return message_id


def _trim(text: str, max_length: int) -> str:
    text = text.strip()
    return text if len(text) <= max_length else f"{text[: max_length - 3]}..."


def build_email_content(
    *,
    watch_headline: str,
    development_summary: str,
    watch_condition: str,
    condition_satisfied: bool,
    sources: list[dict],
) -> tuple[str, str, str]:
    """Deterministic (no model call) subject/text/html for one development
    notification. Returns (subject, text_body, html_body)."""
    condition_met = condition_satisfied and bool(watch_condition.strip())

    if condition_met:
        subject = "Dispatch: Your watch condition was met"
    else:
        subject = f"Dispatch: New development — {_trim(watch_headline, 60)}"

    text_lines = [
        "DISPATCH",
        "",
        "NEW DEVELOPMENT",
        "",
        watch_headline.strip(),
        "",
        development_summary.strip(),
    ]
    if condition_met:
        text_lines += ["", "YOUR WATCH CONDITION WAS MET", "", f'"{watch_condition.strip()}"']
    if sources:
        text_lines += ["", "Sources:"]
        text_lines += [f"- {source['name']} ({source['url']})" for source in sources]
    text_lines += ["", "You received this because you asked Dispatch to watch this story."]
    text_body = "\n".join(text_lines)

    condition_block_html = ""
    if condition_met:
        condition_block_html = f"""
        <p style="margin:24px 0 0;font-family:sans-serif;font-size:12px;letter-spacing:0.08em;
                  text-transform:uppercase;color:#9a5b13;font-weight:600;">
          Your watch condition was met
        </p>
        <p style="margin:4px 0 0;font-family:Georgia,serif;font-style:italic;color:#333;">
          &ldquo;{html.escape(watch_condition.strip())}&rdquo;
        </p>
        """

    sources_html = ""
    if sources:
        links = "".join(
            f'<li style="margin:4px 0;"><a href="{html.escape(source["url"], quote=True)}" '
            f'style="color:#9a5b13;text-decoration:none;">{html.escape(source["name"])}</a></li>'
            for source in sources
        )
        sources_html = f"""
        <p style="margin:24px 0 0;font-family:sans-serif;font-size:12px;letter-spacing:0.08em;
                  text-transform:uppercase;color:#6b6b6b;font-weight:600;">
          Sources
        </p>
        <ul style="margin:8px 0 0;padding-left:18px;font-family:sans-serif;font-size:14px;">{links}</ul>
        """

    html_body = f"""
    <div style="max-width:560px;margin:0 auto;padding:32px 24px;font-family:Georgia,serif;color:#1a1a1a;">
      <p style="margin:0;font-family:sans-serif;font-size:12px;letter-spacing:0.12em;
                text-transform:uppercase;color:#6b6b6b;font-weight:700;">
        Dispatch
      </p>
      <p style="margin:20px 0 0;font-family:sans-serif;font-size:12px;letter-spacing:0.08em;
                text-transform:uppercase;color:#9a5b13;font-weight:600;">
        New development
      </p>
      <h1 style="margin:6px 0 0;font-size:20px;line-height:1.3;">{html.escape(watch_headline.strip())}</h1>
      <p style="margin:16px 0 0;font-size:15px;line-height:1.6;">{html.escape(development_summary.strip())}</p>
      {condition_block_html}
      {sources_html}
      <p style="margin:32px 0 0;font-family:sans-serif;font-size:12px;color:#9a9a9a;">
        You received this because you asked Dispatch to watch this story.
      </p>
    </div>
    """

    return subject, text_body, html_body
