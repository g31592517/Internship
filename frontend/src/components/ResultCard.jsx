import { deadlineLabel, toneClass } from '../lib/format.js'

export default function ResultCard({ opp, application, onOpen }) {
  const dl = deadlineLabel(opp.deadline, opp.expired)
  return (
    <li className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-300">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-slate-900">
            <button className="text-left hover:text-indigo-700 hover:underline" onClick={() => onOpen(false)}>{opp.title}</button>
          </h3>
          <p className="text-sm text-slate-600">{opp.organization || 'Organization not listed'}</p>
        </div>
        <div className={`text-sm ${toneClass[dl.tone]}`}>{dl.text}</div>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        <span className="chip">{opp.opportunity_type}</span>
        {opp.field && <span className="chip">{opp.field}</span>}
        <span className="chip">{opp.location || (opp.remote ? 'Remote' : 'Location not specified')}</span>
        <span className="chip" title="Source website">via {opp.source}</span>
        {opp.location_match === 'unspecified' && <span className="chip bg-amber-50 text-amber-800">Location unclear</span>}
        {opp.can_auto_apply && <span className="chip bg-emerald-50 text-emerald-800">Email application</span>}
      </div>

      {opp.summary && <p className="mt-2 line-clamp-3 text-sm text-slate-600">{opp.summary}</p>}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {application ? (
          <span className="chip bg-indigo-50 text-indigo-800">{application.status} · tracked</span>
        ) : (
          <button className="btn btn-primary" onClick={() => onOpen(true)}>Apply</button>
        )}
        <button className="btn btn-secondary" onClick={() => onOpen(false)}>View details</button>
        <a className="btn btn-ghost" href={opp.url} target="_blank" rel="noopener noreferrer">Original post ↗</a>
        {opp.also_on?.length > 0 && <span className="text-xs text-slate-500">Also on {opp.also_on.map((a) => a.source).join(', ')}</span>}
      </div>
    </li>
  )
}
