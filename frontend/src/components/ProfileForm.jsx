import { useEffect, useState } from 'react'
import { api, setProfileToken } from '../api.js'

const EMPTY = {
  full_name: '', email: '', course: '', phone: '', university: '', year_of_study: '', skills: '',
  linkedin: '', github: '', cover_letter: '',
}

function Field({ id, label, required, hint, children }) {
  return (
    <div>
      <label htmlFor={id} className="label">
        {label} {required ? <span className="text-red-600" aria-hidden="true">*</span> : <span className="font-normal text-slate-500">(optional)</span>}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

export default function ProfileForm({ profile, onSaved }) {
  const [form, setForm] = useState(EMPTY)
  const [cv, setCv] = useState(null)
  const [state, setState] = useState({ busy: false, error: '', ok: '' })

  useEffect(() => {
    if (profile) setForm({ ...EMPTY, ...Object.fromEntries(Object.keys(EMPTY).map((k) => [k, profile[k] ?? ''])) })
  }, [profile])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setState({ busy: true, error: '', ok: '' })
    try {
      let saved = await api.saveProfile(form)
      const token = saved.token          // only on first save
      if (token) setProfileToken(token)  // the CV upload below already needs it
      if (cv) saved = { ...(await api.uploadCv(saved.id, cv)), token }
      setCv(null)
      onSaved(saved)
      setState({ busy: false, error: '', ok: 'Profile saved. It will be used when you apply.' })
    } catch (err) {
      setState({ busy: false, error: err.message, ok: '' })
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-2xl space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Your profile</h1>
        <p className="text-sm text-slate-600">Enter your details once. We use them to fill in applications — you always review before anything is sent.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="p-name" label="Full name" required><input id="p-name" className="input" required minLength={2} value={form.full_name} onChange={set('full_name')} autoComplete="name" /></Field>
        <Field id="p-email" label="Email" required><input id="p-email" type="email" className="input" required value={form.email} onChange={set('email')} autoComplete="email" /></Field>
        <Field id="p-course" label="Course" required><input id="p-course" className="input" required minLength={2} value={form.course} onChange={set('course')} placeholder="e.g. Software Engineering" /></Field>
        <Field id="p-phone" label="Phone"><input id="p-phone" type="tel" className="input" value={form.phone} onChange={set('phone')} autoComplete="tel" /></Field>
        <Field id="p-uni" label="University"><input id="p-uni" className="input" value={form.university} onChange={set('university')} /></Field>
        <Field id="p-year" label="Year of study"><input id="p-year" className="input" value={form.year_of_study} onChange={set('year_of_study')} placeholder="e.g. 3rd year" /></Field>
      </div>
      <Field id="p-skills" label="Skills" hint="Comma separated, e.g. Python, React, SQL"><input id="p-skills" className="input" value={form.skills} onChange={set('skills')} /></Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="p-li" label="LinkedIn"><input id="p-li" className="input" value={form.linkedin} onChange={set('linkedin')} /></Field>
        <Field id="p-gh" label="GitHub"><input id="p-gh" className="input" value={form.github} onChange={set('github')} /></Field>
      </div>
      <Field id="p-cl" label="Short cover note" hint="Added to the email body when you apply by email.">
        <textarea id="p-cl" className="input min-h-24" maxLength={3000} value={form.cover_letter} onChange={set('cover_letter')} />
      </Field>
      <Field id="p-cv" label="CV" hint={profile?.has_cv ? `Current file: ${profile.cv_filename}. Choose a new file to replace it.` : 'PDF, DOC or DOCX, up to 5 MB. Attached to email applications.'}>
        <input id="p-cv" type="file" accept=".pdf,.doc,.docx" className="input" onChange={(e) => setCv(e.target.files?.[0] ?? null)} />
      </Field>

      {state.error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{state.error}</p>}
      {state.ok && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{state.ok}</p>}
      <button className="btn btn-primary" disabled={state.busy}>{state.busy ? 'Saving…' : 'Save profile'}</button>
      <p className="text-xs text-slate-500">
        There’s no password: this browser keeps a private key to your profile. Use the same browser to come back.
        We never ask for, or store, your passwords for other websites.
      </p>
    </form>
  )
}
