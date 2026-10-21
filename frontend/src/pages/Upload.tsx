import { useState, type DragEvent, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { Upload as UploadIcon } from '../components/Icons'
import { TopBar } from '../components/ui'
import { buttonPrimary, input } from '../lib/ui'
import { parse } from '../lib/api'
import { save } from '../lib/storage'

const ACCEPT = '.pdf,.docx'

export default function Upload() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function pick(f: File | undefined) {
    if (!f) return
    setError(/\.(pdf|docx)$/i.test(f.name) ? '' : 'Upload a PDF or Word (.docx) file.')
    setFile(f)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    pick(e.dataTransfer.files[0])
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!file) return setError('Choose your resume first.')
    setBusy(true)
    setError('')
    try {
      const result = await parse(file, text)
      save({ profile: result.profile, filters: result.filters, baseline: result.filters, chat: [], reply: result.reply,
        cityFound: result.home_city_found })
      navigate('/review')
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <>
      <TopBar />
      <main className="mx-auto max-w-[640px] px-4 pb-16 pt-12 sm:pt-20">
        <h1 className="text-[28px] font-bold leading-tight tracking-tight sm:text-[34px]">
          Find STEM internships you can actually land
        </h1>
        <p className="mt-3 max-w-[60ch] text-muted">
          Upload your resume and say what you're looking for. InternMatch ranks open internships by how strong a
          candidate you'd be, and shows a recruiter's reasoning for every score.
        </p>

        <form onSubmit={submit} className="mt-8 space-y-6">
          <div>
            <span className="mb-2 block font-semibold">Your resume</span>
            <label
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center focus-within:outline-2 focus-within:outline-accent ${
                dragging ? 'border-accent bg-accent-soft' : 'border-line-strong bg-surface hover:border-faint'
              }`}
            >
              <UploadIcon className="size-6 text-accent" />
              {file ? (
                <span><span className="font-semibold">{file.name}</span><span className="block text-[13px] text-muted">Click to choose a different file</span></span>
              ) : (
                <span><span className="font-semibold text-accent">Choose a file</span> or drag it here<span className="block text-[13px] text-muted">PDF or Word, up to 5 MB</span></span>
              )}
              <input type="file" accept={ACCEPT} className="sr-only" onChange={(e) => pick(e.target.files?.[0])} />
            </label>
          </div>

          <div>
            <label htmlFor="looking" className="mb-2 block font-semibold">What are you looking for? <span className="font-normal text-muted">(optional)</span></label>
            <textarea
              id="looking"
              rows={3}
              maxLength={1000}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="For example: aerospace positions near LA, hybrid or in person"
              className={`${input} resize-y`}
            />
          </div>

          {error && <p role="alert" className="text-[13px] font-medium text-notmet">{error}</p>}

          <div className="flex flex-wrap items-center gap-4">
            <button type="submit" disabled={busy} className={buttonPrimary}>
              {busy ? 'Reading your resume…' : 'Read my resume'}
            </button>
            {busy && <span className="pulse text-[13px] text-muted">This takes about 15 seconds.</span>}
          </div>
        </form>

        <p className="mt-10 border-t border-line pt-4 text-[13px] text-faint">
          Your resume is read once and not stored. Your profile stays in this browser until you clear it.
        </p>
      </main>
    </>
  )
}
