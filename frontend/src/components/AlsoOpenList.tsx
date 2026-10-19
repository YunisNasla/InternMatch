import { dateLabel, locationLabel } from '../lib/format'
import type { Posting } from '../lib/types'
import { Chevron, External } from './Icons'

export default function AlsoOpenList({ postings, total }: { postings: Posting[]; total: number }) {
  if (!total) return null
  return (
    <details className="group rounded-lg border border-line bg-surface">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-lg px-4 py-3 hover:bg-ground">
        <span>
          <span className="font-semibold">Also open: {total.toLocaleString()} more postings</span>
          <span className="block text-[13px] text-muted">These match your filters but have no description to score. Newest first.</span>
        </span>
        <Chevron className="size-5 shrink-0 text-muted motion-safe:transition-transform group-open:rotate-180" />
      </summary>
      <ul className="divide-y divide-line border-t border-line">
        {postings.map((p) => (
          <li key={p.id} className="flex items-center gap-3 px-4 py-2.5">
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{p.title}</p>
              <p className="truncate text-[13px] text-faint">{p.company} · {locationLabel(p.locations)} · {dateLabel(p)}</p>
            </div>
            <a href={p.url} target="_blank" rel="noreferrer" aria-label={`View ${p.title} at ${p.company}`}
              className="shrink-0 rounded-lg p-1.5 text-muted hover:bg-ground hover:text-ink"><External className="size-4" /></a>
          </li>
        ))}
      </ul>
      {total > postings.length && <p className="border-t border-line px-4 py-2.5 text-[13px] text-muted">Showing the newest {postings.length}. Narrow your filters to see others.</p>}
    </details>
  )
}
