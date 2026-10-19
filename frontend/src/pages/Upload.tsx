import { useEffect, useState } from 'react'
import { getMeta } from '../lib/api'
import type { Meta } from '../lib/types'

// Placeholder until the UI batch: proves the API wiring works.
export default function Upload() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getMeta().then(setMeta, (e: Error) => setError(e.message))
  }, [])

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">InternMatch</h1>
      {error && <p className="mt-4 text-red-700">{error}</p>}
      <ul className="mt-4 list-disc pl-6">
        {meta?.industries.map((i) => <li key={i.code}>{i.label}</li>)}
      </ul>
    </main>
  )
}
