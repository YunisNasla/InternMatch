import { useState, type ReactNode } from 'react'
import { checkCity } from '../lib/api'
import type { Arrangement, Filters, Meta } from '../lib/types'
import { input } from '../lib/ui'
import { Check } from './Icons'

function toggle<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item]
}

function Chip({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) {
  return (
    <button type="button" aria-pressed={on} onClick={onClick}
      className={`inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-[13px] font-medium ${
        on ? 'border-accent bg-accent text-white hover:bg-accent-strong' : 'border-line-strong bg-surface text-ink hover:border-faint'
      }`}>
      {on && <Check className="-ml-1 size-3.5" />}{label}
    </button>
  )
}

function Group({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <fieldset className="border-t border-line pt-5">
      <legend className="sr-only">{title}</legend>
      <p aria-hidden className="font-semibold">{title}</p>
      {hint && <p className="mt-0.5 text-[13px] text-muted">{hint}</p>}
      <div className="mt-3">{children}</div>
    </fieldset>
  )
}

export default function PreferencesForm({ filters, onChange, meta, cityFoundAtParse }: {
  filters: Filters; onChange: (f: Filters) => void; meta: Meta | null; cityFoundAtParse?: boolean
}) {
  const [cityFound, setCityFound] = useState<boolean | null>(cityFoundAtParse === false ? false : null)
  const set = (changes: Partial<Filters>) => onChange({ ...filters, ...changes })
  const remoteOnly = filters.work_arrangements.length === 1 && filters.work_arrangements[0] === 'remote'

  async function verifyCity(value: string) {
    setCityFound(value.trim() ? (await checkCity(value.trim()).catch(() => ({ found: true }))).found : null)
  }

  return (
    <section aria-labelledby="prefs-h" className="space-y-5 rounded-lg border border-line bg-surface p-5 sm:p-6">
      <div>
        <h2 id="prefs-h" className="text-xl font-bold tracking-tight">What you're looking for</h2>
        <p className="mt-1 text-[13px] text-muted">Leave industries or role types empty to see all of them.</p>
      </div>

      <Group title="Role types" hint="The kind of work. Pre-checked from your resume.">
        <div className="space-y-3">
          {meta?.role_type_groups.map((g) => (
            <div key={g.group}>
              <p className="mb-2 text-[13px] font-medium text-muted">{g.group}</p>
              <div className="flex flex-wrap gap-2">
                {g.role_types.map((r) => (
                  <Chip key={r.code} label={r.label} on={filters.role_types.includes(r.code)}
                    onClick={() => set({ role_types: toggle(filters.role_types, r.code) })} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </Group>

      <Group title="Industries" hint="The kind of company.">
        <div className="flex flex-wrap gap-2">
          {meta?.industries.map((i) => (
            <Chip key={i.code} label={i.label} on={filters.industries.includes(i.code)}
              onClick={() => set({ industries: toggle(filters.industries, i.code) })} />
          ))}
        </div>
      </Group>

      <Group title="Location">
        <div className="grid gap-4 sm:grid-cols-[1fr_180px]">
          <div>
            <label htmlFor="home" className="mb-1 block text-[13px] font-medium text-muted">Home city</label>
            <input id="home" className={input} placeholder="City, ST" maxLength={100} value={filters.home_city ?? ''}
              aria-describedby="home-msg" aria-invalid={cityFound === false}
              onChange={(e) => { set({ home_city: e.target.value.trim() ? e.target.value : null }); setCityFound(null) }}
              onBlur={(e) => verifyCity(e.target.value)} />
            <p id="home-msg" className="mt-1 min-h-5 text-[13px] text-notmet">
              {cityFound === false && "City not found. Try City, ST, like Austin, TX. Until then, distance isn't applied."}
              {!filters.home_city && filters.max_distance_miles && !remoteOnly && 'Add a home city to use the distance limit.'}
            </p>
          </div>
          <div>
            <label htmlFor="miles" className="mb-1 block text-[13px] font-medium text-muted">Max distance (miles)</label>
            <input id="miles" type="number" min={1} inputMode="numeric" className={input} placeholder="No limit"
              disabled={remoteOnly} value={remoteOnly ? '' : filters.max_distance_miles ?? ''}
              onChange={(e) => set({ max_distance_miles: Number(e.target.value) > 0 ? Number(e.target.value) : null })} />
            {remoteOnly && <p className="mt-1 text-[13px] text-muted">Not needed for remote only.</p>}
          </div>
        </div>
      </Group>

      <Group title="Work arrangement" hint="Postings that don't say are always included.">
        <div className="flex flex-wrap gap-2">
          {meta?.work_arrangements.filter((a) => a.code !== 'not_stated').map((a) => {
            const code = a.code as Arrangement
            const on = filters.work_arrangements.includes(code)
            return <Chip key={code} label={a.label} on={on}
              onClick={() => (!on || filters.work_arrangements.length > 1) && set({ work_arrangements: toggle(filters.work_arrangements, code) })} />
          })}
        </div>
      </Group>

      <Group title="Term" hint="Postings with no term listed are always included.">
        <div className="flex flex-wrap gap-2">
          {meta?.terms.map((t) => {
            const on = filters.terms.includes(t)
            return <Chip key={t} label={t} on={on} onClick={() => (!on || filters.terms.length > 1) && set({ terms: toggle(filters.terms, t) })} />
          })}
        </div>
      </Group>

      <Group title="More">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="within" className="mb-1 block text-[13px] font-medium text-muted">Posted within</label>
            <select id="within" className={input} value={filters.posted_within_days ?? ''}
              onChange={(e) => set({ posted_within_days: e.target.value ? (Number(e.target.value) as 7 | 30) : null })}>
              <option value="">Any time</option>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
            </select>
          </div>
          <div>
            <label htmlFor="exclude" className="mb-1 block text-[13px] font-medium text-muted">Hide companies (comma separated)</label>
            <input id="exclude" className={input} defaultValue={filters.exclude_companies.join(', ')}
              onBlur={(e) => set({ exclude_companies: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })} />
          </div>
        </div>
      </Group>
    </section>
  )
}
