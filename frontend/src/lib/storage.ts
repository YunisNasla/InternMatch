// Local storage can throw (private mode, blocked site data), so every access is guarded.
export function load<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export function save(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Nothing to do: the app still works without saved data.
  }
}

export function clear(): void {
  try {
    localStorage.clear()
  } catch {
    // Same as above.
  }
}
