import { COUNTIES, COURSE_SUGGESTIONS } from '../lib/format.js'

export default function SearchForm({ query, setQuery, onSearch, loading }) {
  const submit = (e) => {
    e.preventDefault()
    if (query.course.trim().length >= 2) onSearch()
  }
  return (
    <form onSubmit={submit} className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-[1fr_1fr_auto] sm:items-end">
      <div>
        <label htmlFor="course" className="label">Course <span className="text-red-600" aria-hidden="true">*</span></label>
        <input id="course" className="input" list="course-list" required minLength={2} maxLength={120}
          placeholder="e.g. Software Engineering" value={query.course}
          onChange={(e) => setQuery({ ...query, course: e.target.value })} />
        <datalist id="course-list">{COURSE_SUGGESTIONS.map((c) => <option key={c} value={c} />)}</datalist>
      </div>
      <div>
        <label htmlFor="location" className="label">Location <span className="font-normal text-slate-500">(optional)</span></label>
        <input id="location" className="input" list="county-list" placeholder="Any location — or type a county / town"
          value={query.location} onChange={(e) => setQuery({ ...query, location: e.target.value })} />
        <datalist id="county-list">{COUNTIES.map((c) => <option key={c} value={c} />)}</datalist>
      </div>
      <button type="submit" className="btn btn-primary h-[38px]" disabled={loading || query.course.trim().length < 2}>
        {loading ? 'Searching…' : 'Find Opportunities'}
      </button>
    </form>
  )
}
