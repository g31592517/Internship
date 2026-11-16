// Thin client for the FastAPI backend (proxied at /api in development).
const BASE = import.meta.env.VITE_API_BASE ?? '/api'

// Secret returned once when the profile is created; proves this browser owns the profile.
let profileToken = null
export const setProfileToken = (t) => { profileToken = t || null }

async function request(path, { method = 'GET', body, signal, form } = {}) {
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  if (profileToken) headers['X-Profile-Token'] = profileToken
  const res = await fetch(BASE + path, {
    method,
    signal,
    headers,
    body: form ?? (body ? JSON.stringify(body) : undefined),
  })
  let data = null
  try {
    data = await res.json()
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const detail = data?.detail
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg?.replace(/^Value error, /, '')).join('. ')
      : detail || `Request failed (${res.status})`
    const err = new Error(msg)
    err.status = res.status
    throw err
  }
  return data
}

export const api = {
  health: () => request('/health'),
  search: (params, signal) => request('/opportunities/search', { method: 'POST', body: params, signal }),
  opportunity: (id) => request(`/opportunities/${id}`),
  saveProfile: (p) => request('/profile', { method: 'POST', body: p }),
  getProfile: (id) => request(`/profile/${id}`),
  uploadCv: (id, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/profile/${id}/cv`, { method: 'POST', form })
  },
  previewApplication: (profile_id, opportunity_id) =>
    request('/applications/preview', { method: 'POST', body: { profile_id, opportunity_id } }),
  apply: (payload) => request('/applications', { method: 'POST', body: payload }),
  applications: (profile_id) => request(`/applications?profile_id=${profile_id}`),
  updateApplication: (id, patch) => request(`/applications/${id}`, { method: 'PATCH', body: patch }),
}
