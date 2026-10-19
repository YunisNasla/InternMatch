import type { Meta } from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${path} failed with ${res.status}`)
  return res.json()
}

export const getMeta = () => get<Meta>('/api/meta')
