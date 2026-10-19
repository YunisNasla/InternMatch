import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { clear } from '../lib/storage'
import { buttonQuiet } from '../lib/ui'
import { Alert, Info } from './Icons'

export function Notice({ tone = 'warn', children }: { tone?: 'warn' | 'info'; children: ReactNode }) {
  const style = tone === 'warn' ? 'border-warn-line bg-warn-soft' : 'border-line bg-accent-soft'
  return (
    <div role="status" className={`flex gap-2.5 rounded-lg border px-3.5 py-2.5 text-[13px] leading-5 text-ink ${style}`}>
      {tone === 'warn' ? <Alert className="mt-px size-4 shrink-0 text-stretch" /> : <Info className="mt-px size-4 shrink-0 text-accent" />}
      <div>{children}</div>
    </div>
  )
}

export function TopBar({ updated, showClear }: { updated?: string | null; showClear?: boolean }) {
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-surface/95 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-4 px-4 sm:px-6">
        <a href="/" className="text-xl font-bold tracking-tight text-ink no-underline">
          Intern<span className="text-accent">Match</span>
        </a>
        {updated && (
          <span className="hidden text-[13px] text-faint sm:inline">
            Postings updated {new Date(updated).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
          </span>
        )}
        {showClear && (
          <div className="ml-auto flex items-center gap-2">
            {confirming ? (
              <>
                <span className="hidden text-[13px] text-muted sm:inline">Delete your saved profile from this browser?</span>
                <button className={buttonQuiet} onClick={() => setConfirming(false)}>Cancel</button>
                <button
                  className="rounded-lg bg-notmet px-3.5 py-2 font-semibold text-white hover:bg-danger-strong"
                  onClick={() => { clear(); navigate('/', { replace: true }) }}
                >
                  Clear my data
                </button>
              </>
            ) : (
              <button className={buttonQuiet} onClick={() => setConfirming(true)}>Clear my data</button>
            )}
          </div>
        )}
      </div>
    </header>
  )
}
