import { useEffect, useState } from 'react'
import { getMeta } from './api'
import type { Meta } from './types'

export const buttonPrimary =
  'inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 font-semibold text-white hover:bg-accent-strong disabled:cursor-not-allowed disabled:bg-line-strong disabled:text-muted'
export const buttonQuiet =
  'inline-flex items-center justify-center gap-2 rounded-lg border border-line-strong bg-surface px-3.5 py-2 font-medium text-ink hover:bg-ground disabled:cursor-not-allowed disabled:text-faint'
export const input =
  'w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-ink placeholder:text-faint hover:border-faint focus:border-accent focus:outline-none focus-visible:outline-2 focus-visible:outline-accent'

export function useMeta(): Meta | null {
  const [meta, setMeta] = useState<Meta | null>(null)
  useEffect(() => {
    getMeta().then(setMeta, () => setMeta(null))
  }, [])
  return meta
}
