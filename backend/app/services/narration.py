import re

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]


def build_narration(stories: list[dict]) -> tuple[str, list[dict]]:
    """Build narration text + segment metadata from the exact visible headline
    and summary of each saved story, with no rewriting.

    Returns the full narration string to send to ElevenLabs, plus a list of
    {story_id, type, text, char_start, char_end} describing where each piece
    of visible text falls within that string, so alignment timing can later
    be sliced back out by character offset.
    """
    parts: list[str] = []
    segments_meta: list[dict] = []
    cursor = 0

    def emit(text: str) -> None:
        nonlocal cursor
        parts.append(text)
        cursor += len(text)

    for story in stories:
        headline = (story.get("headline") or "").strip()
        if not headline:
            continue

        start = cursor
        emit(headline)
        segments_meta.append(
            {"story_id": story["id"], "type": "headline", "text": headline, "char_start": start, "char_end": cursor}
        )
        emit(" " if headline[-1] in ".!?" else ". ")

        for sentence in split_sentences(story.get("summary") or ""):
            start = cursor
            emit(sentence)
            segments_meta.append(
                {"story_id": story["id"], "type": "summary", "text": sentence, "char_start": start, "char_end": cursor}
            )
            emit(" ")

        emit("\n\n")

    return "".join(parts), segments_meta


def map_segment_timings(
    segments_meta: list[dict],
    narration_text: str,
    characters: list[str] | None,
    start_times: list[float] | None,
    end_times: list[float] | None,
) -> list[dict]:
    """Slice ElevenLabs' character-level alignment back into the visible
    headline/summary segments by character offset.

    Returns an empty list (rather than raising) whenever the alignment data
    is missing or doesn't line up with the text we sent, so the caller can
    still play the generated audio without highlighting.
    """
    if not characters or not start_times or not end_times:
        return []
    if len(characters) != len(narration_text) or len(start_times) != len(characters) or len(end_times) != len(characters):
        return []

    segments: list[dict] = []
    for meta in segments_meta:
        start_idx = meta["char_start"]
        end_idx = meta["char_end"] - 1
        if start_idx < 0 or end_idx < start_idx or end_idx >= len(characters):
            continue
        segments.append(
            {
                "story_id": meta["story_id"],
                "type": meta["type"],
                "text": meta["text"],
                "start": start_times[start_idx],
                "end": end_times[end_idx],
            }
        )
    return segments
