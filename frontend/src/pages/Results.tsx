import { useCallback, useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router'
import AlsoOpenList from '../components/AlsoOpenList'
import RefineChat from '../components/RefineChat'
import ResultCard, { CardPlaceholder } from '../components/ResultCard'
import SearchSummary from '../components/SearchSummary'
import { Notice, TopBar } from '../components/ui'
import { buttonQuiet, useMeta } from '../lib/ui'
import { refine, search } from '../lib/api'
import { recentTurns, resultsSummary } from '../lib/format'
import { load, save } from '../lib/storage'
import type { Card, Filters, Posting, SearchResult, Turn } from '../lib/types'

const FIRST_PAGE = 20

export default function Results() {
  const meta = useMeta()
  const saved = load()
  const profile = saved.profile
  const [filters, setFilters] = useState(saved.filters)
  const [chat, setChat] = useState<Turn[]>(saved.chat ?? [])
  const [cards, setCards] = useState<Card[]>([])
  const [result, setResult] = useState<Omit<SearchResult, 'cards'> | null>(null)
  const [unscored, setUnscored] = useState(0)
  const [nextOffset, setNextOffset] = useState(FIRST_PAGE)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const [asking, setAsking] = useState(false)
  const [askError, setAskError] = useState('')
  const latest = useRef(0) // only the newest search may write results

  const runSearch = useCallback(async (f: Filters) => {
    if (!profile) return
    const id = ++latest.current
    setLoading(true)
    setError('')
    setCards([])
    try {
      const r = await search(profile, f, 0)
      if (id !== latest.current) return
      setCards(r.cards)
      setResult(r)
      setUnscored(r.unscored.length)
      setNextOffset(FIRST_PAGE)
    } catch (e) {
      if (id === latest.current) setError((e as Error).message)
    } finally {
      if (id === latest.current) setLoading(false)
    }
  }, [profile])

  const started = useRef(false)
  useEffect(() => {
    // Search once on arrival (StrictMode runs effects twice in dev, and each search costs scorer calls).
    // Later searches are started by the chat and the chips.
    if (started.current || !filters) return
    started.current = true
    runSearch(filters)
  }, [filters, runSearch])

  if (!profile || !filters) return <Navigate to="/" replace />
  const baseline = saved.baseline ?? filters

  function applyFilters(f: Filters) {
    setFilters(f)
    save({ filters: f })
    runSearch(f)
  }

  async function scoreMore() {
    const id = latest.current
    setLoadingMore(true)
    try {
      const r = await search(profile!, filters!, nextOffset)
      if (id !== latest.current) return
      setCards((prev) => [...prev, ...r.cards.filter((c) => !prev.some((p) => p.id === c.id))])
      setResult((prev) => (prev ? { ...prev, has_more: r.has_more } : prev))
      setUnscored((n) => n + r.unscored.length)
      setNextOffset((o) => o + 10)
    } catch (e) {
      if (id === latest.current) setError((e as Error).message)
    } finally {
      setLoadingMore(false)
    }
  }

  async function ask(message: string) {
    const withQuestion: Turn[] = [...chat, { role: 'student', text: message }]
    setChat(withQuestion)
    setAsking(true)
    setAskError('')
    try {
      const r = await refine(filters!, message, resultsSummary(cards), recentTurns(chat))
      const next: Turn[] = [...withQuestion, { role: 'app' as const, text: r.reply }].slice(-6)
      setChat(next)
      save({ chat: next })
      if (JSON.stringify(r.filters) !== JSON.stringify(filters)) applyFilters(r.filters)
    } catch (e) {
      setAskError((e as Error).message)
      setChat(chat)
    } finally {
      setAsking(false)
    }
  }

  const alsoOpen: Posting[] = result?.also_open ?? []

  return (
    <>
      <TopBar updated={meta?.last_ingest} showClear />
      <main className="mx-auto grid max-w-[1400px] grid-cols-[minmax(0,1fr)] gap-5 px-4 pb-16 pt-6 sm:px-6 lg:grid-cols-[260px_minmax(0,1fr)_340px] lg:items-start">
        <div className="space-y-5 lg:sticky lg:top-20">
          <SearchSummary filters={filters} baseline={baseline} meta={meta}
            onUndo={(field) => applyFilters({ ...filters, [field]: baseline[field] })} busy={asking} />
        </div>

        <div className="order-3 min-w-0 space-y-3 lg:order-none">
          <div className="space-y-2">
            {loading ? (
              <p className="pulse text-muted" role="status">Scoring your top 20 matches. This takes about 20 seconds.</p>
            ) : (
              <p className="text-muted" role="status">
                {cards.length ? `${cards.length} matches scored, ${filters.sort_by === 'posted' ? 'newest first' : 'best fit first'}` : ''}
              </p>
            )}
            {result && !result.home_city_found && (filters.home_city || filters.max_distance_miles) && (
              <Notice>
                {filters.home_city ? `We couldn't find ${filters.home_city}, so distance isn't applied.` : 'Add a home city to use the distance limit.'}
                {' '}Fix it in <a className="font-medium text-accent" href="/review">preferences</a>.
              </Notice>
            )}
            {result && result.hidden_count > 0 && (
              <Notice tone="info">{result.hidden_count} postings hidden because their location couldn't be found.</Notice>
            )}
            {unscored > 0 && <Notice>Couldn't score {unscored} postings right now. Try again in a minute.</Notice>}
            {error && (
              <Notice>{error} <button className="font-semibold text-accent" onClick={() => runSearch(filters)}>Try again</button></Notice>
            )}
          </div>

          {loading
            ? Array.from({ length: 5 }, (_, i) => <CardPlaceholder key={i} />)
            : cards.map((c) => <ResultCard key={c.id} card={c} />)}

          {!loading && !error && cards.length === 0 && (
            <div className="rounded-lg border border-line bg-surface px-5 py-8 text-center">
              <p className="font-semibold">No scored matches for these filters</p>
              <p className="mt-1 text-[13px] text-muted">Remove a filter on the left, or ask the chat to widen your search.</p>
            </div>
          )}

          {loadingMore && Array.from({ length: 3 }, (_, i) => <CardPlaceholder key={`more${i}`} />)}
          {!loading && result?.has_more && (
            <div className="flex items-center gap-3 pt-1">
              <button className={buttonQuiet} disabled={loadingMore} onClick={scoreMore}>
                {loadingMore ? 'Scoring 10 more…' : 'Score 10 more'}
              </button>
              {loadingMore && <span className="text-[13px] text-muted">About 20 seconds.</span>}
            </div>
          )}

          {!loading && <AlsoOpenList postings={alsoOpen} total={result?.also_open_total ?? 0} />}
        </div>

        <div className="order-2 lg:sticky lg:top-20 lg:order-none">
          <RefineChat chat={chat} busy={asking} error={askError} onSend={ask} />
        </div>
      </main>
    </>
  )
}
