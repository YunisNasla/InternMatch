import type { Filters, Profile, Turn } from './types'

// Everything about the student lives only in this browser. Every access is guarded:
// local storage throws in private modes and when site data is blocked.
type Saved = { profile: Profile; filters: Filters; baseline: Filters; chat: Turn[]; reply: string }
const KEY = 'internmatch'

export function load(): Partial<Saved> {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '{}')
  } catch {
    return {}
  }
}

export function save(changes: Partial<Saved>): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({ ...load(), ...changes }))
  } catch {
    // The app still works for this visit without saved data.
  }
}

export function clear(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // Nothing saved to remove.
  }
}
