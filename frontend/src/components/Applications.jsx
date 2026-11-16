import { useState } from 'react'
import { api } from '../api.js'
import { fmtDate } from '../lib/format.js'

const STATUSES = ['Pending', 'Applied', 'Accepted', 'Rejected']
const TONE = {
  Pending: 'bg-slate-100 text-slate-700',
  Applied: 'bg-indigo-50 text-indigo-800',
  Accepted: 'bg-emerald-50 text-emerald-800',
  Rejected: 'bg-red-50 text-red-800',
}

export default function Applications({ profile, applications, reload, goProfile, openOpportunity }) {
  const [error, setError] = useState('')

  if (!profile) {
    return (
      <div className="mx-auto max-w-xl rounded-xl border border-slate-200 bg-white p-6 text-center">
        <p className="mb-3 text-slate-700">Create your profile to track the applications you make.</p>
        <button className="btn btn-primary" onClick={goProfile}>Create profile</button>
      </div>
    )
  }

  const change = async (a, status) => {
    setError('')
    try {
      await api.updateApplication(a.id, { status })
      reload()
    } catch (e) {
      setError(e.message)
    }
  }

  const counts = STATUSES.map((s) => [s, applications.filter((a) => a.status === s).length])

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-1 text-xl font-bold text-slate-900">My applications</h1>
      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        {counts.map(([s, n]) => <span key={s} className={`chip ${TONE[s]}`}>{s}: {n}</span>)}
      </div>
      {error && <p role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}

      {applications.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
          No applications yet. Find an opportunity and apply — it will show up here.
        </div>
      ) : (
        <ul className="space-y-3">
          {applications.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="min-w-0">
                <button className="text-left font-semibold text-slate-900 hover:text-indigo-700 hover:underline" onClick={() => openOpportunity(a.opportunity_id)}>{a.title}</button>
                <p className="text-sm text-slate-600">{a.organization || 'Organization not listed'}</p>
                <p className="text-xs text-slate-500">
                  Applied {fmtDate(a.applied_at)} · {a.method === 'email' ? 'sent by email' : 'on the employer’s site'}
                  {a.notes && ` · ${a.notes}`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <label className="sr-only" htmlFor={`st-${a.id}`}>Status for {a.title}</label>
                <select id={`st-${a.id}`} className={`rounded-lg border-0 px-3 py-1.5 text-sm font-semibold ${TONE[a.status]}`}
                  value={a.status} onChange={(e) => change(a, e.target.value)}>
                  {STATUSES.map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
