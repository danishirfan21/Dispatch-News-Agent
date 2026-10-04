export type WatchUpdateStatus = 'no-change' | 'new-development'

export type LatestMeaningfulChange = {
  heading: string
  detail: string
}

export type WatchedStory = {
  id: string
  category: string
  title: string
  currentStatus: string
  updateStatus: WatchUpdateStatus
  /** ISO timestamp; relative display is derived from it at render time. */
  updatedAt: string

  /** The most recent development worth surfacing to the user. */
  latestMeaningfulChange: LatestMeaningfulChange
  /** What the user has already been told, so we don't repeat ourselves. */
  knownContext: string
  /** Default text for the "Notify me when:" criterion textarea. */
  watchCondition: string
  monitoredSources: string[]
  /** Default state of the "Notify only on major developments" checkbox. */
  majorDevelopmentsOnly: boolean
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
    latestMeaningfulChange: {
      heading: 'Staff-Level Agreement in Place',
      detail:
        'The IMF reached a staff-level agreement for a 37-month, $7.0B Extended Fund Facility. Final sign-off is pending bilateral financing confirmations.',
    },
    knownContext:
      "Staff-level agreement in place, State Bank of Pakistan policy rate held at 19.5% with positive real interest rates calibrated to 12% inflation, and provincial agricultural income tax legislation tabled in Punjab and Sindh assemblies.",
    watchCondition:
      'Pakistan and the IMF formally reach an agreement and the Executive Board signs off on the disbursement.',
    monitoredSources: [
      'IMF Press Office',
      'Ministry of Finance',
      'State Bank of Pakistan',
      'Bloomberg',
      'Reuters',
    ],
    majorDevelopmentsOnly: true,
  },
  {
    id: 'openai-reasoning-release',
    category: 'Autonomous Systems',
    title: 'OpenAI Frontier Reasoning Architecture & Model Release',
    currentStatus: 'New technical pre-print published with verified benchmarks',
    updateStatus: 'new-development',
    updatedAt: minutesAgoTimestamp(4),
    latestMeaningfulChange: {
      heading: 'Benchmark Pre-Print Published',
      detail:
        'A new technical publication reveals self-correcting inference routines that reduce error rates on advanced mathematical and software benchmarks.',
    },
    knownContext:
      'Prior releases focused on scaling pre-training; this is the first public benchmark suite built around runtime, multi-step verification rather than raw model size.',
    watchCondition: 'A general-availability release date or pricing is announced.',
    monitoredSources: ['arXiv Preprint', 'Nature Machine Intelligence', 'MIT Tech Review'],
    majorDevelopmentsOnly: true,
  },
  {
    id: 'semiconductor-export-controls',
    category: 'Trade & Geopolitics',
    title: 'US-China Advanced Semiconductor Equipment Export Controls',
    currentStatus: 'Inter-agency directives finalized among allied equipment manufacturers',
    updateStatus: 'no-change',
    updatedAt: minutesAgoTimestamp(120),
    latestMeaningfulChange: {
      heading: 'Export Rules Finalized',
      detail:
        'The Commerce Department finalized expanded restrictions on advanced transistor tooling and high-bandwidth memory packaging equipment.',
    },
    knownContext:
      'Coordinated policy discussions are underway with allied equipment manufacturers in Tokyo and The Hague; no new restricted entities have been added since the initial announcement.',
    watchCondition: 'Any allied government announces matching or diverging export rules.',
    monitoredSources: ['Wall Street Journal', 'South China Morning Post', 'Nikkei Asia'],
    majorDevelopmentsOnly: true,
  },
  {
    id: 'ntsb-rudder-directive',
    category: 'Regulatory / Aviation',
    title: 'NTSB Narrowbody Rudder Control Airworthiness Directives',
    currentStatus: 'Fleet inspection underway with zero grounding events',
    updateStatus: 'no-change',
    updatedAt: minutesAgoTimestamp(180),
    latestMeaningfulChange: {
      heading: 'Emergency Inspections Ordered',
      detail:
        'Federal safety regulators instructed operators to carry out immediate borescope inspections across 410 narrowbody aircraft after a potential thermal-binding issue was identified.',
    },
    knownContext:
      'Inspections are underway across the affected fleet; no aircraft have been grounded and no incidents have been reported during cold-weather descents since the directive was issued.',
    watchCondition: 'Any aircraft is grounded, or the inspection deadline is extended.',
    monitoredSources: ['FlightGlobal', 'Aviation Week', 'Reuters Aerospace'],
    majorDevelopmentsOnly: false,
  },
]
