import { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { deadlineLabel, fmtDate, toneClass } from '../lib/format.js'
import ApplyPanel from './ApplyPanel.jsx'

export default function OpportunityModal({ id, focusApply, profile, application, onClose, onApplied, goProfile }) {
  const [opp, setOpp] = useState(null)
  const [error, setError] = useState('')
  const applyRef = useRef(null)
  const closeRef = useRef(null)

  useEffect(() => {
    let live = true
    api.opportunity(id).then((o) => live && setOpp(o)).catch((e) => live && setError(e.message))
    return () => { live = false }
  }, [id])

  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onCloseRef.current()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    closeRef.current?.focus()
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [])

  useEffect(() => {
    if (opp && focusApply) applyRef.current?.scrollIntoView({ block: 'center' })
  }, [opp, focusApply])

  const dl = opp && deadlineLabel(opp.deadline, opp.expired)

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 p-0 sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label={opp ? opp.title : 'Opportunity'}
        className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-t-2xl bg-white shadow-xl sm:rounded-2xl">
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-slate-900">{opp ? opp.title : 'Loading…'}</h2>
            {opp && <p className="text-slate-600">{opp.organization || 'Organization not listed'}</p>}
          </div>
          <button ref={closeRef} onClick={onClose} className="btn btn-secondary !px-3" aria-label="Close">✕</button>
        </div>

        <div className="space-y-5 px-5 py-4">
          {error && <div role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{error}</div>}
          {!opp && !error && <p className="text-slate-500">Loading opportunity…</p>}

          {opp && (
            <>
              <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
                <Item label="Type" value={opp.opportunity_type} />
                <Item label="Course / field" value={opp.field || 'Not specified'} />
                <Item label="Location" value={opp.location || (opp.remote ? 'Remote' : 'Not specified')} />
                <Item label="Deadline" value={<span className={toneClass[dl.tone]}>{dl.text}</span>} />
                {opp.posted_date && <Item label="Posted" value={fmtDate(opp.posted_date)} />}
                <Item label="Source" value={<a className="text-indigo-700 underline" href={opp.url} target="_blank" rel="noopener noreferrer">{opp.source} ↗</a>} />
              </dl>

              {opp.requirements.length > 0 && (
                <section>
                  <h3 className="mb-1 font-semibold text-slate-900">Requirements</h3>
                  <ul className="list-disc space-y-0.5 pl-5 text-sm text-slate-700">
                    {opp.requirements.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </section>
              )}

              <section>
                <h3 className="mb-1 font-semibold text-slate-900">Description</h3>
                {opp.description
                  ? <div className="max-h-72 overflow-y-auto whitespace-pre-line rounded-lg bg-slate-50 p-3 text-sm leading-relaxed text-slate-700">{opp.description}</div>
                  : <p className="text-sm text-slate-500">No description was available from the source. See the original post for details.</p>}
              </section>

              <div ref={applyRef}>
                <ApplyPanel opp={opp} profile={profile} application={application} goProfile={goProfile} onApplied={onApplied} />
              </div>

              {opp.also_on?.length > 0 && (
                <p className="text-xs text-slate-500">
                  Also listed on: {opp.also_on.map((a, i) => (
                    <span key={a.url}>{i > 0 && ', '}<a className="underline" href={a.url} target="_blank" rel="noopener noreferrer">{a.source}</a></span>
                  ))}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function Item({ label, value }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-slate-800">{value}</dd>
    </div>
  )
}
