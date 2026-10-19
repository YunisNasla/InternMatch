export type Option = { code: string; label: string }

export type Meta = {
  industries: Option[]
  role_type_groups: { group: string; role_types: Option[] }[]
  work_arrangements: Option[]
  terms: string[]
  last_ingest: string | null
}

export type Skills = {
  programming_languages: string[]
  frameworks_libraries: string[]
  software_tools: string[]
  hardware_fabrication: string[]
  lab_techniques: string[]
  domain_knowledge: string[]
}

export type Profile = {
  is_stem: boolean
  name: string | null
  location: { city: string | null; state: string | null }
  education: { school: string; degree: string | null; major: string | null; grad_date: string | null; gpa: number | null }[]
  class_standing: 'freshman' | 'sophomore' | 'junior' | 'senior' | 'masters' | 'phd' | 'unknown'
  skills: Skills
  experience: { title: string; org: string; start: string | null; end: string | null; highlights: string[] }[]
  projects: { name: string; tech: string[]; summary: string }[]
  coursework: string[]
  certifications: string[]
  suggested_role_types: string[]
  parse_warnings: string[]
}

export type Arrangement = 'in_person' | 'hybrid' | 'remote'

export type Filters = {
  industries: string[]
  role_types: string[]
  home_city: string | null
  max_distance_miles: number | null
  work_arrangements: Arrangement[]
  terms: string[]
  posted_within_days: 7 | 30 | null
  exclude_companies: string[]
  include_keywords: string[]
  exclude_keywords: string[]
  emphasis: string | null
  sort_by: 'fit_score' | 'posted'
}

export type Tier = 'strong' | 'good' | 'stretch' | 'long_shot'

export type Score = {
  requirements: { requirement: string; type: 'must' | 'nice' | 'inferred'; evidence: string; status: 'met' | 'partial' | 'not_met' }[]
  eligibility: { gate: string; status: 'pass' | 'fail' | 'needs_check'; note: string }[]
  fit_score: number
  tier: Tier
  confidence: 'high' | 'medium' | 'low'
  top_matches: string[]
  key_gaps: string[]
  recruiter_note: string
  resume_tip: string
}

export type Posting = {
  id: string
  company: string
  title: string
  locations: string[]
  url: string
  posted_at: string | null
  date_kind: 'posted' | 'updated' | 'unknown'
  work_arrangement: Arrangement | 'not_stated'
  terms: string[]
  industry: string | null
  role_type: string | null
}

export type Card = Posting & { score: Score }

export type SearchResult = {
  cards: Card[]
  also_open: Posting[]
  also_open_total: number
  hidden_count: number
  has_more: boolean
  home_city_found: boolean
  unscored: { id: string; company: string; title: string; url: string }[]
}

export type ParseResult = { profile: Profile; filters: Filters; reply: string; is_stem: boolean; home_city_found: boolean }

export type RefineResult = { intent: 'update_filters' | 'explain' | 'clarify'; reply: string; filters: Filters }

export type Turn = { role: 'student' | 'app'; text: string }
