import { daysLeft } from '../lib/format.js'

export const DEFAULT_FILTERS = { field: '', organization: '', county: '', deadline: 'any', sort: 'relevance' }

export function applyFilters(results, f) {
  let out = results.filter((o) => {
    if (f.field && o.field !== f.field) return false
    if (f.organization && o.organization !== f.organization) return false
    if (f.county === '__none__' ? o.counties.length > 0 : f.county && !o.counties.includes(f.county)) return false
    if (f.deadline !== 'any') {
      if (!o.deadline) return false
      const n = daysLeft(o.deadline)
      if (f.deadline === '7' && n > 7) return false
      if (f.deadline === '30' && n > 30) return false
    }
    return true
  })
  const by = {
    deadline: (a, b) => (a.deadline || '9999').localeCompare(b.deadline || '9999'),
    newest: (a, b) => (b.posted_date || '').localeCompare(a.posted_date || ''),
    relevance: null,
  }[f.sort]
  if (by) out = [...out].sort(by)
  return out
}

function Select({ id, label, value, onChange, children }) {
  return (
    <div>
      <label htmlFor={id} className="label">{label}</label>
      <select id={id} className="input" value={value} onChange={(e) => onChange(e.target.value)}>{children}</select>
    </div>
  )
}

export default function Filters({ facets, filters, setFilters }) {
  const set = (k) => (v) => setFilters({ ...filters, [k]: v })
  const dirty = JSON.stringify(filters) !== JSON.stringify(DEFAULT_FILTERS)
  return (
    <aside aria-label="Filters" className="h-fit space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:sticky lg:top-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-900">Filters</h2>
        {dirty && <button className="text-sm text-indigo-700 underline" onClick={() => setFilters(DEFAULT_FILTERS)}>Reset</button>}
      </div>
      <Select id="f-location" label="Location" value={filters.county} onChange={set('county')}>
        <option value="">All locations</option>
        {facets.locations.map((c) => <option key={c} value={c}>{c}</option>)}
        <option value="__none__">Location not specified</option>
      </Select>
      <Select id="f-field" label="Course / field" value={filters.field} onChange={set('field')}>
        <option value="">All fields</option>
        {facets.fields.map((c) => <option key={c} value={c}>{c}</option>)}
      </Select>
      <Select id="f-org" label="Organization" value={filters.organization} onChange={set('organization')}>
        <option value="">All organizations</option>
        {facets.organizations.map((c) => <option key={c} value={c}>{c}</option>)}
      </Select>
      <Select id="f-deadline" label="Deadline" value={filters.deadline} onChange={set('deadline')}>
        <option value="any">Any time</option>
        <option value="7">Within 7 days</option>
        <option value="30">Within 30 days</option>
      </Select>
      <Select id="f-sort" label="Sort by" value={filters.sort} onChange={set('sort')}>
        <option value="relevance">Best match</option>
        <option value="deadline">Deadline (soonest)</option>
        <option value="newest">Newest</option>
      </Select>
    </aside>
  )
}
