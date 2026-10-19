import { useId, useState } from 'react'
import { arrangementLabel, dateLabel, locationLabel, termLabel, TIER_LABEL } from '../lib/format'
import type { Card, Score, Tier } from '../lib/types'
import { Chevron, External, Met, NotMet, Partial, Question } from './Icons'

/** The note's first sentence leads in bold; the rest supports it in regular weight. */
function splitNote(note: string): [string, string] {
  const at = note.search(/[.!?]\s/)
  return at < 0 ? [note, ''] : [note.slice(0, at + 1), note.slice(at + 2)]
}

const TIER_STYLE: Record<Tier, string> = {
  strong: 'bg-strong-soft text-strong',
  good: 'bg-good-soft text-good',
  stretch: 'bg-stretch-soft text-stretch',
  long_shot: 'bg-longshot-soft text-longshot',
}

const STATUS = {
  met: { Icon: Met, label: 'Met', color: 'text-met' },
  partial: { Icon: Partial, label: 'Partial', color: 'text-partial' },
  not_met: { Icon: NotMet, label: 'Not met', color: 'text-notmet' },
}

const TYPE_LABEL = { must: 'Required', nice: 'Nice to have', inferred: 'Implied' }

/** A match's short label: the words before its colon ("Hands-on bring-up: fixed two..."), else the whole line. */
function matchLabel(m: string): string {
  const head = m.split(':')[0]
  return head.length < m.length && head.length <= 48 ? head : m
}

function WhyThisScore({ score, note }: { score: Score; note: string }) {
  const checks = score.eligibility.filter((g) => g.status !== 'pass')
  return (
    <div className="fade-in mt-4 space-y-4 border-t border-line pt-4">
      {note && <p className="max-w-[70ch] text-ink">{note}</p>}
      {score.top_matches.length > 0 && (
        <div>
          <p className="text-[13px] font-semibold">What matches</p>
          <ul className="mt-1 space-y-1">
            {score.top_matches.map((m) => (
              <li key={m} className="flex gap-2 text-[13px] leading-5 text-muted"><Met className="mt-0.5 size-4 shrink-0 text-met" />{m}</li>
            ))}
          </ul>
        </div>
      )}
      <table className="w-full text-left text-[13px] leading-5">
        <caption className="sr-only">Each requirement in the posting and the evidence for it on your profile</caption>
        <thead className="text-faint">
          <tr>
            <th scope="col" className="pb-2 pr-3 font-medium">Requirement</th>
            <th scope="col" className="w-[104px] pb-2 pr-3 font-medium">Status</th>
            <th scope="col" className="hidden pb-2 font-medium sm:table-cell">Your evidence</th>
          </tr>
        </thead>
        <tbody>
          {score.requirements.map((r, i) => {
            const s = STATUS[r.status]
            return (
              <tr key={i} className="border-t border-line align-top">
                <td className="py-2 pr-3">
                  <span className="text-ink">{r.requirement}</span>
                  <span className="block text-faint">{TYPE_LABEL[r.type]}</span>
                  <span className="mt-1 block text-muted sm:hidden">{r.evidence}</span>
                </td>
                <td className={`py-2 pr-3 font-medium ${s.color}`}>
                  <span className="inline-flex items-center gap-1.5"><s.Icon className="size-4 shrink-0" />{s.label}</span>
                </td>
                <td className="hidden py-2 text-muted sm:table-cell">{r.evidence}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {checks.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {checks.map((g, i) => (
            <span key={i} title={g.note}
              className="inline-flex items-center gap-1.5 rounded-lg bg-longshot-soft px-2.5 py-1 text-[13px] text-longshot">
              <Question className="size-4" />{g.status === 'needs_check' ? `Check: ${g.gate}` : `Doesn't fit: ${g.gate}`}
            </span>
          ))}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {score.key_gaps.length > 0 && (
          <div>
            <p className="text-[13px] font-semibold">Gaps to know about</p>
            <ul className="mt-1 list-disc pl-4 text-[13px] leading-5 text-muted">{score.key_gaps.map((g) => <li key={g}>{g}</li>)}</ul>
          </div>
        )}
        <div>
          <p className="text-[13px] font-semibold">Resume tip</p>
          <p className="mt-1 text-[13px] leading-5 text-muted">{score.resume_tip}</p>
        </div>
      </div>
    </div>
  )
}

export default function ResultCard({ card }: { card: Card }) {
  const [open, setOpen] = useState(false)
  const panel = useId()
  const s = card.score
  const [lead, rest] = splitNote(s.recruiter_note)
  const pill = <span className={`rounded-lg px-2 py-0.5 text-[13px] font-semibold ${TIER_STYLE[s.tier]}`}>{TIER_LABEL[s.tier]}</span>
  return (
    <article className="fade-in rounded-lg border border-line bg-surface p-4 hover:border-line-strong sm:p-5">
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          {/* Phones: pill and score share the top row so the verdict gets the full width. */}
          <div className="mb-1.5 flex items-center justify-between sm:hidden">
            {pill}
            <span className="tabular text-[20px] font-bold text-ink">{s.fit_score}<span className="text-[13px] font-normal text-faint"> / 100</span></span>
          </div>
          <p className="font-semibold leading-6 text-ink">
            <span className="mr-2 hidden align-[1px] sm:inline">{pill}</span>{lead}
          </p>
          <h3 className="mt-1.5 text-ink">
            <span className="font-semibold">{card.company}</span> <span className="text-muted">· {card.title}</span>
          </h3>
          <p className="mt-0.5 text-[13px] text-faint">
            {locationLabel(card.locations)} · {arrangementLabel(card.work_arrangement)} · {termLabel(card.terms)} · {dateLabel(card)}
          </p>
          {s.top_matches.length > 0 && (
            <ul className="mt-2.5 flex flex-wrap gap-1.5" aria-label="Top matches">
              {s.top_matches.map((m) => (
                <li key={m} title={m} className="inline-flex max-w-full items-center gap-1.5 rounded-lg bg-ground px-2 py-1 text-[13px] text-muted">
                  <Met className="size-3.5 shrink-0 text-met" /><span className="truncate">{matchLabel(m)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="hidden shrink-0 text-right sm:block">
          <p className="tabular text-[20px] font-bold leading-none text-ink" aria-label={`Fit score ${s.fit_score} out of 100`}>{s.fit_score}</p>
          <p className="mt-1 text-[13px] text-faint" aria-hidden>out of 100</p>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2">
        <button type="button" aria-expanded={open} aria-controls={panel} onClick={() => setOpen(!open)}
          className="inline-flex items-center gap-1 font-semibold text-accent hover:text-accent-strong">
          Why this score <Chevron className={`size-4 motion-safe:transition-transform motion-safe:duration-200 ${open ? 'rotate-180' : ''}`} />
        </button>
        <a href={card.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-muted hover:text-ink">
          View posting <External className="size-4" />
        </a>
      </div>
      <div id={panel} hidden={!open}>{open && <WhyThisScore score={s} note={rest} />}</div>
    </article>
  )
}

export function CardPlaceholder() {
  return (
    <div aria-hidden className="pulse rounded-lg border border-line bg-surface p-5">
      <div className="flex gap-4">
        <div className="flex-1 space-y-2.5">
          <div className="h-5 w-3/4 rounded bg-line" />
          <div className="h-4 w-1/2 rounded bg-ground" />
          <div className="h-3.5 w-2/3 rounded bg-ground" />
        </div>
        <div className="h-8 w-12 rounded bg-line" />
      </div>
    </div>
  )
}
