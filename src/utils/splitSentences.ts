const SENTENCE_SPLIT_RE = /(?<=[.!?])\s+/

export function splitSentences(text: string): string[] {
  const trimmed = text.trim()
  if (!trimmed) return []
  return trimmed
    .split(SENTENCE_SPLIT_RE)
    .map((part) => part.trim())
    .filter(Boolean)
}
