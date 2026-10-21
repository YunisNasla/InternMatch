import type { Filters, Profile, Turn } from './types'

// Everything about the student lives only in this browser. Every access is guarded:
// local storage throws in private modes and when site data is blocked.
type Saved = { profile: Profile; filters: Filters; baseline: Filters; chat: Turn[]; reply: string; cityFound: boolean }
// Bump the version when the saved shape or the supported terms change: old data is then dropped,
// instead of failing every search on a field or term the server no longer accepts.
const PREFIX = 'internmatch'
const KEY = `${PREFIX}:v1`

export function load(): Partial<Saved> {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) ?? '{}')
    return saved && typeof saved === 'object' && !Array.isArray(saved) ? saved : {}
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
    // Older versions too, so nothing about the student is left behind.
    Object.keys(localStorage).filter((k) => k.startsWith(PREFIX)).forEach((k) => localStorage.removeItem(k))
  } catch {
    // Nothing saved to remove.
  }
}
