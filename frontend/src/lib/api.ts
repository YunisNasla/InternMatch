import type { Filters, Meta, ParseResult, Profile, RefineResult, SearchResult } from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new Error("Can't reach InternMatch right now. Check your connection and try again.")
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    // FastAPI returns a plain string for our own errors and a list for validation errors.
    const detail = typeof body?.detail === 'string' ? body.detail : 'Something went wrong. Try again.'
    throw new Error(detail)
  }
  return res.json()
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const getMeta = () => request<Meta>('/api/meta')

export function parse(file: File, text: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('text', text)
  return request<ParseResult>('/api/parse', { method: 'POST', body: form })
}

export const search = (profile: Profile, filters: Filters, offset: number) =>
  request<SearchResult>('/api/search', json({ profile, filters, offset }))

export const refine = (filters: Filters, message: string, results_summary: string, recent_turns: string) =>
  request<RefineResult>('/api/refine', json({ filters, message, results_summary, recent_turns }))

export const checkCity = (q: string) =>
  request<{ found: boolean }>(`/api/city?q=${encodeURIComponent(q)}`)
