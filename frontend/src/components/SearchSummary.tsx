import { Link } from 'react-router'
import { changedFields, describe } from '../lib/format'
import type { Filters, Meta } from '../lib/types'
import { Close } from './Icons'

const SHOWN: (keyof Filters)[] = ['role_types', 'industries', 'home_city', 'max_distance_miles', 'work_arrangements', 'terms']

export default function SearchSummary({ filters, baseline, meta, onUndo }: {
  filters: Filters; baseline: Filters; meta: Meta | null; onUndo: (field: keyof Filters) => void
}) {
  const changed = changedFields(filters, baseline)
  return (
    <section aria-labelledby="search-h" className="rounded-lg border border-line bg-surface p-4">
      <div className="flex items-baseline justify-between gap-2">
        <h2 id="search-h" className="font-semibold">Your search</h2>
        <Link to="/review" className="text-[13px] font-medium text-accent hover:text-accent-strong">Edit preferences</Link>
      </div>
      {/* Phones: one line, so the first result reaches the first screen. */}
      <p className="mt-1 line-clamp-2 text-[13px] leading-5 text-muted lg:hidden">
        {[describe('home_city', baseline, meta), describe('role_types', baseline, meta)].join(' · ')}
      </p>
      <ul className="mt-2 hidden space-y-1 text-[13px] leading-5 text-muted lg:block">
        {SHOWN.filter((f) => !changed.includes(f)).map((f) => <li key={f}>{describe(f, baseline, meta)}</li>)}
      </ul>
      {changed.length > 0 && (
        <>
          <p className="mt-3 text-[13px] font-semibold lg:mt-4">Changed in chat</p>
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {changed.map((f) => (
              <li key={f}>
                <button type="button" onClick={() => onUndo(f)} aria-label={`Undo: ${describe(f, filters, meta)}`}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent-soft py-1 pl-2.5 pr-1.5 text-left text-[13px] font-medium text-accent-strong hover:border-accent">
                  {describe(f, filters, meta)} <Close className="size-3.5 shrink-0" />
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
