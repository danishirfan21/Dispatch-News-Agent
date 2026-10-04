export function minutesSince(isoTimestamp: string): number {
  return (Date.now() - new Date(isoTimestamp).getTime()) / 60_000
}

export function formatRelativeTime(minutesAgo: number): string {
  if (minutesAgo < 1) return 'just now'
  if (minutesAgo < 60) return `${Math.round(minutesAgo)}m ago`

  const hoursAgo = Math.round(minutesAgo / 60)
  if (hoursAgo < 24) return `${hoursAgo}h ago`

  const daysAgo = Math.round(hoursAgo / 24)
  return `${daysAgo}d ago`
}
