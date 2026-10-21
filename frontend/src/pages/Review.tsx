import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import PreferencesForm from '../components/PreferencesForm'
import ProfilePanel from '../components/ProfilePanel'
import { Notice, TopBar } from '../components/ui'
import { buttonPrimary, useMeta } from '../lib/ui'
import { load, save } from '../lib/storage'

export default function Review() {
  const navigate = useNavigate()
  const meta = useMeta()
  const saved = load()
  const [profile, setProfile] = useState(saved.profile)
  const [filters, setFilters] = useState(saved.filters)
  if (!profile || !filters) return <Navigate to="/" replace />

  function seeMatches() {
    // The page 2 filters become the baseline the chat's changes are measured against.
    save({ profile, filters, baseline: filters, chat: [] })
    navigate('/results')
  }

  return (
    <>
      <TopBar updated={meta?.last_ingest} showClear />
      <main className="mx-auto max-w-[920px] space-y-5 px-4 pb-28 pt-8 sm:px-6">
        <div>
          <h1 className="text-xl font-bold leading-tight tracking-tight">Check what we read</h1>
          <p className="mt-2 text-muted">Make any fixes, then see your matches.</p>
        </div>

        {saved.reply && <Notice tone="info">{saved.reply}</Notice>}
        {!profile.is_stem && (
          <Notice>InternMatch is built for STEM students, so results may be thin for your field. You can still continue.</Notice>
        )}
        {profile.parse_warnings.length > 0 && (
          <Notice>
            <p className="font-semibold">Double-check these</p>
            <ul className="mt-1 list-disc pl-4">{profile.parse_warnings.map((w) => <li key={w}>{w}</li>)}</ul>
          </Notice>
        )}

        <ProfilePanel profile={profile} onChange={setProfile} />
        <PreferencesForm filters={filters} onChange={setFilters} meta={meta} cityFoundAtParse={saved.cityFound} />
      </main>

      <div className="fixed inset-x-0 bottom-0 border-t border-line bg-surface/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[920px] items-center justify-end gap-3 px-4 py-3 sm:px-6">
          <span className="hidden text-[13px] text-muted sm:inline">We'll score your top 20 matches. It takes about 20 seconds.</span>
          <button className={buttonPrimary} onClick={seeMatches}>See my matches</button>
        </div>
      </div>
    </>
  )
}
