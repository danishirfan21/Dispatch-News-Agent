export type BriefStory = {
  id: string
  category: string
  /** Minutes elapsed since publication, used to derive a relative timestamp. */
  minutesAgo: number
  headline: string
  summary: string
  whyItMatters: string
  sources: string[]
}

export const mockBriefStories: BriefStory[] = [
  {
    id: 'pakistan-imf-efb',
    category: "Pakistan's Economy",
    minutesAgo: 14,
    headline:
      'IMF Executive Board Convenes on $7B Extended Fund Facility as Islamabad Meets Fiscal Milestones',
    summary:
      "The International Monetary Fund enters final technical review of Pakistan's 37-month loan program. Key conditions around provincial tax harmonization and power tariff restructuring show early compliance, though external financing gaps of $2.1B remain under negotiation with bilateral lenders in Riyadh and Beijing.",
    whyItMatters:
      "You're seeing this because you follow Pakistan's economy and IMF negotiations. This development could materially affect Pakistan's financing outlook.",
    sources: ['Financial Times', 'Dawn News', 'Bloomberg', 'Reuters'],
  },
  {
    id: 'openai-reasoning-benchmarks',
    category: 'Artificial Intelligence',
    minutesAgo: 60,
    headline:
      'OpenAI Unveils Reasoning Architecture Benchmarks Demonstrating Multi-Step Verification',
    summary:
      'A new technical publication reveals self-correcting inference routines that substantially reduce error rates across advanced mathematical and competitive software benchmarks, signalling a pivotal industry pivot from pure pre-training scale toward runtime computation.',
    whyItMatters:
      "You're seeing this because you track AI research and frontier foundation models. These reasoning benchmarks indicate a paradigm shift in autonomous problem-solving.",
    sources: ['arXiv Preprint', 'Nature Machine Intelligence', 'MIT Tech Review'],
  },
  {
    id: 'semiconductor-export-controls',
    category: 'US-China Relations',
    minutesAgo: 120,
    headline:
      'Commerce Department Finalizes Expanded Semiconductor Export Controls Targeting Advanced Packaging',
    summary:
      'New administrative directives extend international restrictions to cutting-edge transistor tooling and high-bandwidth memory packaging equipment, prompting coordinated policy discussions with allied equipment manufacturers in Tokyo and The Hague.',
    whyItMatters:
      "You're seeing this because you follow US-China relations and semiconductor policy. New export restrictions will immediately impact supply chain equipment flows.",
    sources: ['Wall Street Journal', 'South China Morning Post', 'Nikkei Asia'],
  },
  {
    id: 'narrowbody-airworthiness-directive',
    category: 'Aviation Safety',
    minutesAgo: 180,
    headline:
      'NTSB Issues Urgent Airworthiness Directive on Rudder Control Assembly After Narrowbody Review',
    summary:
      'Federal safety regulators have instructed operators to carry out immediate borescope inspections across 410 narrowbody passenger aircraft after investigators identified potential thermal binding in dual-servo valve actuators during cold-weather descents.',
    whyItMatters:
      'You\'re seeing this because you monitor major aviation safety directives. The emergency inspections directly impact commercial narrowbody fleet scheduling.',
    sources: ['FlightGlobal', 'Aviation Week', 'Reuters Aerospace'],
  },
  {
    id: 'ufc-light-heavyweight-title',
    category: 'Combat Sports',
    minutesAgo: 300,
    headline:
      'Light Heavyweight Championship Bout Confirmed for UFC 312 as Contender Secures Unanimous Decision',
    summary:
      'Promotion executives have concluded contract terms in Las Vegas following requisite medical clearances, establishing a marquee headline clash of stylistic specialists scheduled for the autumn pay-per-view slate in Sydney.',
    whyItMatters:
      "You're seeing this because you track UFC championship bouts. The title fight rescheduling alters the division's title timeline.",
    sources: ['MMA Fighting', 'ESPN MMA'],
  },
]
