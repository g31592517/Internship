export const COURSE_SUGGESTIONS = [
  'Software Engineering', 'Computer Science', 'Information Technology', 'Business Administration',
  'Electrical Engineering', 'Civil Engineering', 'Mechanical Engineering', 'Accounting', 'Finance',
  'Economics', 'Nursing', 'Clinical Medicine', 'Pharmacy', 'Public Health', 'Education', 'Law',
  'Journalism', 'Public Relations', 'Marketing', 'Human Resource Management', 'Supply Chain Management',
  'Agriculture', 'Environmental Science', 'Hospitality Management', 'Tourism', 'Statistics',
  'Public Administration', 'Social Work', 'Architecture', 'Data Science',
]

export const COUNTIES = [
  'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Kiambu', 'Machakos', 'Kajiado', 'Uasin Gishu', 'Kisii', 'Kakamega',
  'Nyeri', 'Meru', 'Kilifi', 'Kwale', 'Embu', 'Kericho', 'Bungoma', 'Busia', 'Siaya', 'Homa Bay', 'Migori',
  'Nyamira', 'Narok', 'Laikipia', 'Garissa', 'Turkana', 'Kitui', 'Makueni', 'Murang\'a', 'Kirinyaga', 'Nandi',
  'Trans Nzoia', 'Baringo', 'Bomet', 'Vihiga', 'Taita Taveta', 'Lamu', 'Isiolo', 'Marsabit', 'Nyandarua',
  'Tharaka Nithi', 'Elgeyo Marakwet', 'West Pokot', 'Samburu', 'Tana River', 'Wajir', 'Mandera',
]

export function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso.length <= 10 ? iso + 'T00:00:00' : iso)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function daysLeft(iso) {
  if (!iso) return null
  const d = new Date(iso + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((d - today) / 86400000)
}

export function deadlineLabel(iso, expired) {
  if (!iso) return { text: 'No deadline listed', tone: 'muted' }
  if (expired) return { text: `Closed ${fmtDate(iso)}`, tone: 'bad' }
  const n = daysLeft(iso)
  if (n <= 0) return { text: 'Closes today', tone: 'warn' }
  if (n <= 7) return { text: `${n} day${n === 1 ? '' : 's'} left · ${fmtDate(iso)}`, tone: 'warn' }
  return { text: `Deadline ${fmtDate(iso)}`, tone: 'ok' }
}

export const toneClass = {
  muted: 'text-slate-500',
  ok: 'text-slate-700',
  warn: 'text-amber-700 font-medium',
  bad: 'text-red-700 font-medium',
}
