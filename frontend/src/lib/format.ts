import type { Card, Filters, Meta, Posting, Tier, Turn } from './types'

export const TIER_LABEL: Record<Tier, string> = {
  strong: 'Strong fit', good: 'Good fit', stretch: 'Stretch', long_shot: 'Long shot',
}

const ARRANGEMENT_LABEL = { in_person: 'In person', hybrid: 'Hybrid', remote: 'Remote', not_stated: 'Arrangement not listed' }

export function arrangementLabel(a: Posting['work_arrangement']): string {
  return ARRANGEMENT_LABEL[a]
}

export function termLabel(terms: string[]): string {
  const known = terms.filter((t) => t !== 'unknown')
  return known.length ? known.join(', ') : 'Term not listed'
}

export function locationLabel(locations: string[]): string {
  if (!locations.length) return 'Location not listed'
  return locations.length === 1 ? locations[0] : `${locations[0]} + ${locations.length - 1} more`
}

function ago(iso: string): string {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (days < 1) return 'today'
  if (days === 1) return '1 day ago'
  if (days < 14) return `${days} days ago`
  if (days < 60) return `${Math.floor(days / 7)} weeks ago`
  return `${Math.floor(days / 30)} months ago`
}

export function dateLabel(p: Pick<Posting, 'posted_at' | 'date_kind'>): string {
  if (!p.posted_at || p.date_kind === 'unknown') return 'Date unknown'
  return `${p.date_kind === 'posted' ? 'Posted' : 'Updated'} ${ago(p.posted_at)}`
}

function labels(codes: string[], options: { code: string; label: string }[]): string {
  return codes.map((c) => options.find((o) => o.code === c)?.label ?? c).join(', ')
}

function short(list: string, max = 2): string {
  const parts = list.split(', ')
  return parts.length > max ? `${parts.slice(0, max).join(', ')} + ${parts.length - max} more` : list
}

type Field = keyof Filters

/** One line per filter, in the words a student would use. */
export function describe(field: Field, f: Filters, meta: Meta | null): string {
  const roles = meta?.role_type_groups.flatMap((g) => g.role_types) ?? []
  switch (field) {
    case 'industries': return f.industries.length ? `Industries: ${short(labels(f.industries, meta?.industries ?? []))}` : 'All industries'
    case 'role_types': return f.role_types.length ? `Roles: ${short(labels(f.role_types, roles))}` : 'All role types'
    case 'home_city': return f.home_city ? `Near ${f.home_city}` : 'No home city'
    case 'max_distance_miles': return f.max_distance_miles ? `Within ${f.max_distance_miles} mi` : 'Any distance'
    case 'work_arrangements': return f.work_arrangements.length === 3 ? 'Any arrangement' : f.work_arrangements.map((a) => ARRANGEMENT_LABEL[a]).join(' or ')
    case 'terms': return f.terms.join(', ')
    case 'posted_within_days': return f.posted_within_days ? `Posted in the last ${f.posted_within_days} days` : 'Any posting date'
    case 'exclude_companies': return f.exclude_companies.length ? `Hiding ${short(f.exclude_companies.join(', '))}` : 'No hidden companies'
    case 'include_keywords': return f.include_keywords.length ? `Must mention ${f.include_keywords.join(', ')}` : 'No required words'
    case 'exclude_keywords': return f.exclude_keywords.length ? `Skipping ${f.exclude_keywords.join(', ')}` : 'No skipped words'
    case 'emphasis': return f.emphasis ? `Weighing: ${f.emphasis}` : 'No extra weighting'
    case 'sort_by': return f.sort_by === 'posted' ? 'Newest first' : 'Best fit first'
  }
}

/** Fields the chat changed from the page 2 baseline; each becomes an undoable chip. */
export function changedFields(f: Filters, baseline: Filters): Field[] {
  return (Object.keys(f) as Field[]).filter((k) => JSON.stringify(f[k]) !== JSON.stringify(baseline[k]))
}

const SUMMARY_LIMIT = 6000 // the /api/refine cap

/** The results summary Prompt 4 reads: company | title | location | score | tier | top gaps. Top 20 cards only. */
export function resultsSummary(cards: Card[]): string {
  return cards.slice(0, 20).map((c) => [
    c.company, c.title, c.locations.join('; '), c.score.fit_score, c.score.tier, c.score.key_gaps.slice(0, 2).join('; '),
  ].join(' | ')).join('\n').slice(0, SUMMARY_LIMIT)
}

export function recentTurns(chat: Turn[]): string {
  return chat.slice(-6).map((t) => `${t.role === 'student' ? 'Student' : 'InternMatch'}: ${t.text}`).join('\n')
}
