import { useState } from 'react'
import { api } from '../api.js'
import { fmtDate } from '../lib/format.js'

// Apply flow:  Apply Automatically -> review exactly what will be sent -> explicit confirm -> send -> recorded.
//              Open Application    -> opens the employer's page -> "I applied" records it for tracking.
export default function ApplyPanel({ opp, profile, application, goProfile, onApplied }) {
  const [stage, setStage] = useState('idle') // idle | loading | review | sending
  const [draft, setDraft] = useState(null)
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [opened, setOpened] = useState(false)
  const [busy, setBusy] = useState(false)

  const applyUrl = opp.apply_url || opp.url

  if (application) {
    return (
      <Box tone="ok">
        <p className="font-medium text-slate-900">You applied to this opportunity.</p>
        <p className="text-sm text-slate-600">
          Status: <strong>{application.status}</strong> · {fmtDate(application.applied_at)}
          {application.method === 'email' ? ' · sent by email' : ' · applied on the employer’s site'}
        </p>
        <p className="mt-1 text-sm text-slate-500">Update the status any time under “My applications”.</p>
      </Box>
    )
  }

  if (opp.expired) {
    return (
      <Box tone="warn">
        <p className="font-medium text-slate-900">This opportunity has closed.</p>
        <a className="btn btn-secondary mt-2" href={applyUrl} target="_blank" rel="noopener noreferrer">View original post ↗</a>
      </Box>
    )
  }

  const startAuto = async () => {
    setError(''); setNotice(''); setStage('loading')
    try {
      const d = await api.previewApplication(profile.id, opp.id)
      setDraft(d); setSubject(d.subject); setBody(d.body); setConfirmed(false)
      if (d.can_auto_apply) setStage('review')
      else { setNotice(d.note || 'Automatic sending is not available for this opportunity.'); setStage('idle') }
    } catch (e) {
      setError(e.message); setStage('idle')
    }
  }

  const send = async () => {
    setError(''); setStage('sending')
    try {
      await api.apply({ profile_id: profile.id, opportunity_id: opp.id, mode: 'auto', confirm: true, subject, body })
      onApplied()
    } catch (e) {
      setError(e.message); setStage('review')
    }
  }

  const track = async (status) => {
    setError(''); setBusy(true)
    try {
      await api.apply({ profile_id: profile.id, opportunity_id: opp.id, mode: 'manual', status })
      onApplied()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  // Send it from the student's own mailbox instead (their email app opens with everything pre-filled).
  const mailto = opp.apply_email
    ? `mailto:${opp.apply_email}?subject=${encodeURIComponent(subject || draft?.subject || `Application for ${opp.title}`)}&body=${encodeURIComponent(body || draft?.body || '')}`
    : null

  return (
    <Box>
      <h3 className="mb-2 font-semibold text-slate-900">Apply</h3>

      {!profile && (
        <p className="mb-3 rounded-lg bg-indigo-50 p-3 text-sm text-indigo-900">
          Create your profile once and we’ll use it for every application.{' '}
          <button className="font-semibold underline" onClick={goProfile}>Create profile</button>
        </p>
      )}

      {stage === 'review' && draft ? (
        <div className="space-y-3">
          <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
            <strong>Review before sending.</strong> Nothing has been sent yet. This is exactly what will be emailed.
          </p>
          <dl className="grid gap-2 rounded-lg border border-slate-200 p-3 text-sm sm:grid-cols-2">
            {draft.fields.map((f) => (
              <div key={f.label}><dt className="text-xs uppercase tracking-wide text-slate-500">{f.label}</dt><dd className="break-all">{f.value}</dd></div>
            ))}
            <div><dt className="text-xs uppercase tracking-wide text-slate-500">Attachments</dt>
              <dd>{draft.attachments.length ? draft.attachments.join(', ') : 'None'}</dd></div>
          </dl>
          {draft.note && <p className="text-sm text-slate-600">{draft.note}</p>}
          {draft.dry_run && <p className="text-sm font-medium text-amber-800">Dry-run mode: nothing will actually be sent.</p>}
          <div><label className="label" htmlFor="subj">Subject</label>
            <input id="subj" className="input" value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} /></div>
          <div><label className="label" htmlFor="body">Message</label>
            <textarea id="body" className="input min-h-48 font-mono text-[13px]" value={body} onChange={(e) => setBody(e.target.value)} /></div>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
            <span>I have reviewed this application and want it sent to <strong>{draft.to}</strong>.</span>
          </label>
          <div className="flex gap-2">
            <button className="btn btn-primary" disabled={!confirmed || stage === 'sending' || !subject.trim() || !body.trim()} onClick={send}>
              {stage === 'sending' ? 'Sending…' : 'Send application'}
            </button>
            <button className="btn btn-secondary" onClick={() => setStage('idle')} disabled={stage === 'sending'}>Cancel</button>
          </div>
          {mailto && (
            <p className="text-sm text-slate-600">
              Prefer to send it from your own email account?{' '}
              <a className="font-medium text-indigo-700 underline" href={mailto}
                onClick={() => { setOpened(true); setStage('idle') }}>Open it in my email app</a>
              {' '}— attach your CV there, send it, then come back and choose “Yes, I applied — track it”.
            </p>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {opp.can_auto_apply && (
            <button className="btn btn-primary" disabled={!profile || stage === 'loading'} onClick={startAuto}>
              {stage === 'loading' ? 'Preparing…' : 'Apply Automatically'}
            </button>
          )}
          <a className={`btn ${opp.can_auto_apply ? 'btn-secondary' : 'btn-primary'}`} href={applyUrl} target="_blank"
            rel="noopener noreferrer" onClick={() => setOpened(true)}>Open Application ↗</a>
        </div>
      )}

      {stage !== 'review' && !opp.can_auto_apply && (
        <p className="mt-2 text-sm text-slate-500">
          This employer takes applications on its own site (or behind a login), so we can’t fill it in for you. Open the
          application, then record it here so you can track it.
        </p>
      )}

      {notice && (
        <p className="mt-3 rounded-lg bg-slate-100 p-3 text-sm text-slate-700">
          {notice} {mailto && <a className="font-medium text-indigo-700 underline" href={mailto}>Open in my email app</a>}
        </p>
      )}
      {error && <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}

      {profile && stage !== 'review' && (
        <div className="mt-4 border-t border-slate-200 pt-3 text-sm">
          <p className="mb-2 text-slate-700">{opened ? 'Did you submit your application?' : 'Applied somewhere else already?'}</p>
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-secondary" disabled={busy} onClick={() => track('Applied')}>Yes, I applied — track it</button>
            <button className="btn btn-ghost" disabled={busy} onClick={() => track('Pending')}>Track as pending</button>
          </div>
        </div>
      )}
    </Box>
  )
}

function Box({ children, tone }) {
  const cls = tone === 'ok' ? 'border-emerald-200 bg-emerald-50' : tone === 'warn' ? 'border-amber-200 bg-amber-50' : 'border-slate-200 bg-white'
  return <section className={`rounded-xl border p-4 ${cls}`}>{children}</section>
}
