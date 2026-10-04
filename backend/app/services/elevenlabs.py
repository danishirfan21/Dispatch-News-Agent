import logging

import httpx

from ..config import settings

logger = logging.getLogger("elevenlabs")


class ElevenLabsError(Exception):
    """Raised for any ElevenLabs-related failure. Message is safe to show the user."""


async def transcribe_audio(audio_bytes: bytes, content_type: str) -> dict:
    """Send audio to ElevenLabs Speech-to-Text and return a normalized result.

    Never returns ElevenLabs' raw response — only the fields the frontend needs.
    """
    if not settings.elevenlabs_api_key:
        logger.error("ElevenLabs transcription skipped: API key is not configured")
        raise ElevenLabsError("Voice dictation isn't configured on the server yet.")

    if not audio_bytes:
        raise ElevenLabsError("No audio was recorded. Please try again.")

    files = {"file": ("recording", audio_bytes, content_type or "application/octet-stream")}
    data = {"model_id": settings.elevenlabs_stt_model}
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.elevenlabs_base_url}/speech-to-text",
                headers=headers,
                data=data,
                files=files,
            )
    except httpx.TimeoutException as exc:
        logger.error("ElevenLabs request timed out: %s", type(exc).__name__)
        raise ElevenLabsError("Transcription took too long to respond. Please try again.") from exc
    except httpx.RequestError as exc:
        logger.error("ElevenLabs request failed: %s", type(exc).__name__)
        raise ElevenLabsError("Couldn't reach the transcription service. Please try again.") from exc

    if response.status_code == 422:
        logger.error("ElevenLabs rejected the audio: unprocessable")
        raise ElevenLabsError("That recording couldn't be transcribed. Please try again.")

    if response.status_code != 200:
        logger.error("ElevenLabs returned an error status=%s", response.status_code)
        raise ElevenLabsError("The transcription service returned an error. Please try again.")

    try:
        body = response.json()
    except ValueError as exc:
        logger.error("ElevenLabs response was not valid JSON: %s", type(exc).__name__)
        raise ElevenLabsError("The transcription service sent back something we couldn't read.") from exc

    text = body.get("text", "").strip()
    language_code = body.get("language_code", "")

    if not text:
        raise ElevenLabsError("Couldn't make out any speech in that recording. Please try again.")

    return {"text": text, "language_code": language_code}
