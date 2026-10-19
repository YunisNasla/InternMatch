import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { Turn } from '../lib/types'
import { Send } from './Icons'

export default function RefineChat({ chat, busy, error, onSend }: {
  chat: Turn[]; busy: boolean; error: string; onSend: (message: string) => void
}) {
  const [text, setText] = useState('')
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'nearest' }) // returns a Promise in new browsers, so never return it
  }, [chat.length, busy])

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!text.trim() || busy) return
    onSend(text.trim())
    setText('')
  }

  return (
    <section aria-labelledby="chat-h" className="flex flex-col rounded-lg border border-line bg-surface lg:h-[calc(100vh-7rem)]">
      <h2 id="chat-h" className="px-4 pt-3 font-semibold lg:border-b lg:border-line lg:pb-3">Refine your results</h2>
      {/* Phones: only the latest reply shows, so the transcript never pushes results off the first screen. */}
      <p className="px-4 pt-1 text-[13px] leading-5 text-muted lg:hidden" aria-live="polite">
        {busy ? 'Thinking…' : chat.length ? chat[chat.length - 1].text : 'Ask in plain words, like "only within 30 miles".'}
      </p>
      <div className="hidden flex-1 space-y-3 overflow-y-auto px-4 py-4 lg:block" aria-live="polite">
        {chat.length === 0 && (
          <p className="text-[13px] leading-5 text-muted">
            Ask in plain words. Try "only within 30 miles", "I care more about hands-on lab work", or "why is the first one a stretch?"
          </p>
        )}
        {chat.map((t, i) => (
          <p key={i} className={`max-w-[92%] rounded-lg px-3 py-2 text-[13px] leading-5 ${
            t.role === 'student' ? 'ml-auto bg-accent text-white' : 'bg-ground text-ink'}`}>
            {t.text}
          </p>
        ))}
        {busy && <p className="pulse max-w-[92%] rounded-lg bg-ground px-3 py-2 text-[13px] text-muted">Thinking…</p>}
        <div ref={end} />
      </div>
      {error && <p role="alert" className="px-4 pb-2 text-[13px] font-medium text-notmet">{error}</p>}
      <form onSubmit={submit} className="flex gap-2 p-3 lg:border-t lg:border-line">
        <label htmlFor="ask" className="sr-only">Ask for a change</label>
        <input id="ask" value={text} maxLength={500} onChange={(e) => setText(e.target.value)}
          placeholder="Ask for a change…"
          className="min-w-0 flex-1 rounded-lg border border-line-strong px-3 py-2 placeholder:text-faint focus:border-accent focus:outline-none" />
        <button type="submit" disabled={busy || !text.trim()} aria-label="Send"
          className="rounded-lg bg-accent px-3 text-white hover:bg-accent-strong disabled:bg-line-strong">
          <Send className="size-5" />
        </button>
      </form>
    </section>
  )
}
