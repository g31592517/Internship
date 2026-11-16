import { useCallback, useEffect, useRef, useState } from 'react'
import { api, setProfileToken } from './api.js'
import SearchForm from './components/SearchForm.jsx'
import Filters, { applyFilters, DEFAULT_FILTERS } from './components/Filters.jsx'
import ResultCard from './components/ResultCard.jsx'
import SourceStatus from './components/SourceStatus.jsx'
import OpportunityModal from './components/OpportunityModal.jsx'
import ProfileForm from './components/ProfileForm.jsx'
import Applications from './components/Applications.jsx'

// { id, token, fields } — this browser's key to its profile, plus a copy of the details so the profile can be
// re-created if the server loses its data (Render's free plan wipes it on every restart / sleep).
const PROFILE_KEY = 'internship-finder.profile'
const PROFILE_FIELDS = ['full_name', 'email', 'course', 'phone', 'university', 'year_of_study', 'skills',
  'linkedin', 'github', 'cover_letter']

const readStored = () => {
  try {
    const v = JSON.parse(localStorage.getItem(PROFILE_KEY) || 'null')
    return v?.id && v?.token ? v : null
  } catch {
    return null
  }
}
const writeStored = (v) => {
  try { localStorage.setItem(PROFILE_KEY, JSON.stringify(v)) } catch { /* ignore */ }
}
const pickFields = (p) => Object.fromEntries(PROFILE_FIELDS.map((k) => [k, p[k] ?? '']))

export default function App() {
  const [view, setView] = useState('search')
  const [profile, setProfile] = useState(null)
  const [applications, setApplications] = useState([])
  const [query, setQuery] = useState({ course: '', location: '' })
  const [search, setSearch] = useState({ status: 'idle', data: null, error: '' })
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [open, setOpen] = useState(null) // { id, focusApply }
  const [notice, setNotice] = useState('')
  const abortRef = useRef(null)

  const onProfileSaved = useCallback((p) => {
    const { token, ...rest } = p
    const tok = token || readStored()?.token   // the token is only returned when the profile is created
    if (token) setProfileToken(token)
    if (tok) writeStored({ id: rest.id, token: tok, fields: pickFields(rest) })
    setProfile(rest)
  }, [])

  // restore the saved profile (no accounts: this browser holds the profile's token)
  useEffect(() => {
    const saved = readStored()
    if (!saved) return
    setProfileToken(saved.token)
    api.getProfile(saved.id).then(onProfileSaved).catch(async (e) => {
      // act only if the server says it doesn't exist (not when the server is asleep / unreachable)
      if (e.status !== 404) return
      setProfileToken(null)
      if (saved.fields?.email) {
        try {   // the server lost its data: re-create the profile from this browser's copy
          onProfileSaved(await api.saveProfile(saved.fields))
          setNotice('The server was restarted and lost its saved data, so we restored your profile from this browser. ' +
            'Please re-upload your CV on the Profile page. Applications tracked before the restart were cleared.')
          return
        } catch { /* fall through */ }
      }
      try { localStorage.removeItem(PROFILE_KEY) } catch { /* ignore */ }
    })
  }, [onProfileSaved])

  const loadApplications = useCallback(async (p) => {
    if (!p) return setApplications([])
    try {
      setApplications(await api.applications(p.id))
    } catch {
      setApplications([])
    }
  }, [])

  useEffect(() => { loadApplications(profile) }, [profile, loadApplications])

  // prefill the course from the profile, once
  useEffect(() => {
    if (profile?.course) setQuery((q) => (q.course ? q : { ...q, course: profile.course }))
  }, [profile])

  const runSearch = async (q, refresh = false) => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setSearch((s) => ({ status: 'loading', data: refresh ? s.data : null, error: '' }))
    setFilters(DEFAULT_FILTERS)
    try {
      const data = await api.search({ course: q.course.trim(), location: q.location.trim(), refresh }, ctrl.signal)
      setSearch({ status: 'done', data, error: '' })
    } catch (e) {
      if (e.name === 'AbortError') return
      setSearch({ status: 'error', data: null, error: e.message })
    }
  }

  const appliedMap = Object.fromEntries(applications.map((a) => [a.opportunity_id, a]))
  const data = search.data
  const shown = data ? applyFilters(data.results, filters) : []

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <button onClick={() => setView('search')} className="text-lg font-bold tracking-tight text-indigo-700">
            Internship Finder
          </button>
          <nav className="flex gap-1 text-sm" aria-label="Main">
            {[['search', 'Find opportunities'], ['applications', `My applications${applications.length ? ` (${applications.length})` : ''}`], ['profile', 'Profile']].map(([id, label]) => (
              <button
                key={id}
                onClick={() => setView(id)}
                aria-current={view === id ? 'page' : undefined}
                className={`rounded-md px-3 py-1.5 font-medium ${view === id ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="ml-auto text-sm text-slate-500">
            {profile ? <>Signed in as <span className="font-medium text-slate-700">{profile.full_name}</span></> : (
              <button className="text-indigo-700 underline" onClick={() => setView('profile')}>Create your profile</button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {notice && (
          <div role="status" className="mb-4 flex items-start justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <span>{notice}</span>
            <button className="font-semibold underline" onClick={() => setNotice('')}>Dismiss</button>
          </div>
        )}
        {view === 'search' && (
          <>
            <section className="mb-6">
              <h1 className="mb-1 text-2xl font-bold text-slate-900">Find your internship or attachment</h1>
              <p className="mb-4 text-slate-600">Enter your course. Add a location if you want to stay close to home.</p>
              <SearchForm query={query} setQuery={setQuery} loading={search.status === 'loading'} onSearch={() => runSearch(query)} />
            </section>

            {search.status === 'loading' && (
              <div role="status" className="rounded-xl border border-slate-200 bg-white p-6 text-center text-slate-600">
                <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
                Searching job sites for <strong>{query.course}</strong>
                {query.location && <> near <strong>{query.location}</strong></>}…
                <div className="mt-1 text-sm text-slate-500">The first search for a course takes up to a minute; repeat searches are instant.</div>
              </div>
            )}

            {search.status === 'error' && (
              <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
                Something went wrong: {search.error}. Check that the backend is running and try again.
              </div>
            )}

            {data && search.status !== 'error' && (
              <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
                <Filters facets={data.facets} filters={filters} setFilters={setFilters} />
                <section aria-live="polite">
                  <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                    <h2 className="text-lg font-semibold text-slate-900">
                      {shown.length} opportunit{shown.length === 1 ? 'y' : 'ies'}
                      <span className="font-normal text-slate-500">
                        {' '}for {data.course}{data.location ? ` in ${data.location}` : ''}
                      </span>
                    </h2>
                    <button className="btn btn-ghost !px-2 !py-1" onClick={() => runSearch(query, true)} disabled={search.status === 'loading'}>
                      Refresh results
                    </button>
                  </div>
                  <SourceStatus sources={data.sources} />
                  {shown.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
                      {data.results.length
                        ? 'No results match your filters.'
                        : <>No open opportunities found for <strong>{data.course}</strong>{data.location ? <> in <strong>{data.location}</strong></> : ''}. Try a broader course name{data.location ? ' or clear the location' : ''}.</>}
                    </div>
                  ) : (
                    <ul className="space-y-3">
                      {shown.map((o) => (
                        <ResultCard key={o.id} opp={o} application={appliedMap[o.id]}
                          onOpen={(focusApply) => setOpen({ id: o.id, focusApply })} />
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            )}
          </>
        )}

        {view === 'applications' && (
          <Applications profile={profile} applications={applications} reload={() => loadApplications(profile)}
            goProfile={() => setView('profile')} openOpportunity={(id) => setOpen({ id })} />
        )}
        {view === 'profile' && <ProfileForm profile={profile} onSaved={onProfileSaved} />}
      </main>

      {open && (
        <OpportunityModal
          id={open.id}
          focusApply={open.focusApply}
          profile={profile}
          application={appliedMap[open.id]}
          onClose={() => setOpen(null)}
          onApplied={() => loadApplications(profile)}
          goProfile={() => { setOpen(null); setView('profile') }}
        />
      )}
    </div>
  )
}
