import { useState } from 'react'
import type { Profile, Skills } from '../lib/types'
import { input } from '../lib/ui'

const SKILL_LABELS: Record<keyof Skills, string> = {
  programming_languages: 'Programming languages',
  frameworks_libraries: 'Frameworks and libraries',
  software_tools: 'Software and tools',
  hardware_fabrication: 'Hardware and fabrication',
  lab_techniques: 'Lab techniques',
  domain_knowledge: 'Domain knowledge',
}
const STANDINGS = ['freshman', 'sophomore', 'junior', 'senior', 'masters', 'phd', 'unknown'] as const
const STANDING_LABEL: Record<(typeof STANDINGS)[number], string> = {
  freshman: 'Freshman', sophomore: 'Sophomore', junior: 'Junior', senior: 'Senior', masters: "Master's", phd: 'PhD', unknown: 'Not sure',
}

/** A comma-separated list that keeps its own text while typing and commits on blur. */
function ListField({ id, label, value, onChange }: { id: string; label: string; value: string[]; onChange: (v: string[]) => void }) {
  const [text, setText] = useState(value.join(', '))
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-[13px] font-medium text-muted">{label}</label>
      {/* Grows with its text, so no parsed value is ever cut off. */}
      <textarea
        id={id}
        rows={Math.max(1, Math.ceil(text.length / 44))}
        className={`${input} resize-none [field-sizing:content]`}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => onChange(text.split(',').map((s) => s.trim()).filter(Boolean))}
      />
    </div>
  )
}

function TextField({ id, label, value, onChange }: { id: string; label: string; value: string | null; onChange: (v: string | null) => void }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-[13px] font-medium text-muted">{label}</label>
      <input id={id} className={input} value={value ?? ''} onChange={(e) => onChange(e.target.value.trim() ? e.target.value : null)} />
    </div>
  )
}

export default function ProfilePanel({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  const edu = profile.education[0] ?? { school: '', degree: null, major: null, grad_date: null, gpa: null }
  const setEdu = (changes: Partial<typeof edu>) => onChange({ ...profile, education: [{ ...edu, ...changes }, ...profile.education.slice(1)] })
  const setSkill = (k: keyof Skills, v: string[]) => onChange({ ...profile, skills: { ...profile.skills, [k]: v } })

  return (
    <section aria-labelledby="profile-h" className="rounded-lg border border-line bg-surface p-5 sm:p-6">
      <h2 id="profile-h" className="text-xl font-bold tracking-tight">Your profile</h2>
      <p className="mt-1 text-[13px] text-muted">Read from your resume. Fix anything that's off; scores use what's here.</p>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <TextField id="name" label="Name" value={profile.name} onChange={(name) => onChange({ ...profile, name })} />
        <div className="grid grid-cols-[1fr_88px] gap-3">
          <TextField id="city" label="City" value={profile.location.city} onChange={(city) => onChange({ ...profile, location: { ...profile.location, city } })} />
          <TextField id="state" label="State" value={profile.location.state} onChange={(state) => onChange({ ...profile, location: { ...profile.location, state } })} />
        </div>
        <TextField id="school" label="School" value={edu.school || null} onChange={(school) => setEdu({ school: school ?? '' })} />
        <TextField id="major" label="Major" value={edu.major} onChange={(major) => setEdu({ major })} />
        <TextField id="grad" label="Graduation (YYYY-MM)" value={edu.grad_date} onChange={(grad_date) => setEdu({ grad_date })} />
        <div>
          <label htmlFor="standing" className="mb-1 block text-[13px] font-medium text-muted">Class standing</label>
          <select id="standing" className={input} value={profile.class_standing}
            onChange={(e) => onChange({ ...profile, class_standing: e.target.value as Profile['class_standing'] })}>
            {STANDINGS.map((s) => <option key={s} value={s}>{STANDING_LABEL[s]}</option>)}
          </select>
        </div>
      </div>

      <h3 className="mt-7 font-semibold">Skills</h3>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        {(Object.keys(SKILL_LABELS) as (keyof Skills)[]).map((k) => (
          <ListField key={k} id={k} label={SKILL_LABELS[k]} value={profile.skills[k]} onChange={(v) => setSkill(k, v)} />
        ))}
        <div className="sm:col-span-2">
          <ListField id="coursework" label="Coursework" value={profile.coursework} onChange={(coursework) => onChange({ ...profile, coursework })} />
        </div>
      </div>

      {(profile.experience.length > 0 || profile.projects.length > 0) && (
        <>
          <h3 className="mt-7 font-semibold">Experience and projects</h3>
          <ul className="mt-3 space-y-3">
            {profile.experience.map((x, i) => (
              <li key={`x${i}`} className="text-[13px] leading-5">
                <span className="font-semibold text-ink">{x.title}</span>, {x.org}
                <span className="text-faint"> · {x.start ?? '?'} to {x.end ?? '?'}</span>
                <ul className="mt-1 list-disc pl-5 text-muted">{x.highlights.map((h, j) => <li key={j}>{h}</li>)}</ul>
              </li>
            ))}
            {profile.projects.map((p, i) => (
              <li key={`p${i}`} className="text-[13px] leading-5">
                <span className="font-semibold text-ink">{p.name}</span>
                <span className="text-muted">: {p.summary}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
