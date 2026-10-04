export type WatchUpdateStatus = 'no-change' | 'new-development'

export type WatchedStory = {
  id: string
  category: string
  title: string
  currentStatus: string
  updateStatus: WatchUpdateStatus
  /** ISO timestamp; relative display is derived from it at render time. */
  updatedAt: string
}

function minutesAgoTimestamp(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString()
}

export const mockWatchedStories: WatchedStory[] = [
  {
    id: 'pakistan-imf-efb',
    category: 'Sovereign Debt',
    title: 'Pakistan & IMF $7.0B Extended Fund Facility',
    currentStatus: 'Awaiting Executive Board Approval',
    updateStatus: 'no-change',
    updatedAt: minutesAgoTimestamp(12),
  },
  {
    id: 'openai-reasoning-release',
    category: 'Autonomous Systems',
    title: 'OpenAI Frontier Reasoning Architecture & Model Release',
    currentStatus: 'New technical pre-print published with verified benchmarks',
    updateStatus: 'new-development',
    updatedAt: minutesAgoTimestamp(4),
  },
  {
    id: 'semiconductor-export-controls',
    category: 'Trade & Geopolitics',
    title: 'US-China Advanced Semiconductor Equipment Export Controls',
    currentStatus: 'Inter-agency directives finalized among allied equipment manufacturers',
    updateStatus: 'no-change',
    updatedAt: minutesAgoTimestamp(120),
  },
  {
    id: 'ntsb-rudder-directive',
    category: 'Regulatory / Aviation',
    title: 'NTSB Narrowbody Rudder Control Airworthiness Directives',
    currentStatus: 'Fleet inspection underway with zero grounding events',
    updateStatus: 'no-change',
    updatedAt: minutesAgoTimestamp(180),
  },
]
