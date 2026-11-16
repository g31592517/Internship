import { useState } from 'react'

const LABEL = {
  ok: 'searched',
  blocked: 'blocked by bot protection — skipped',
  unavailable: 'unavailable right now',
  error: 'error',
}

export default function SourceStatus({ sources }) {
  const [open, setOpen] = useState(false)
  const problems = sources.filter((s) => s.status !== 'ok')
  return (
    <div className="mb-3 text-sm text-slate-500">
      Searched {sources.length - problems.length} of {sources.length} sources
      {problems.length > 0 && <span className="text-amber-700"> · {problems.map((p) => p.name).join(', ')} unavailable</span>}
      <button className="ml-2 text-indigo-700 underline" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? 'Hide' : 'Details'}
      </button>
      {open && (
        <ul className="mt-2 grid gap-1 rounded-lg border border-slate-200 bg-white p-3 sm:grid-cols-2">
          {sources.map((s) => (
            <li key={s.name} className="flex justify-between gap-2">
              <span className="font-medium text-slate-700">{s.name}</span>
              <span className={s.status === 'ok' ? 'text-slate-600' : 'text-amber-700'}>
                {s.status === 'ok' ? `${s.relevant} relevant of ${s.found}` : LABEL[s.status]}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
