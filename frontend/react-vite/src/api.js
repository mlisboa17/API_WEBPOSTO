import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token helpers
export function getToken() {
  try { return localStorage.getItem('WEBPOSTO_TOKEN') }
  catch { return null }
}
export function setToken(token) {
  try {
    if (token) localStorage.setItem('WEBPOSTO_TOKEN', token)
    else localStorage.removeItem('WEBPOSTO_TOKEN')
  } catch (e) {}
  api.defaults.headers.common['Authorization'] = token ? `Bearer ${token}` : undefined
}

// initialize from storage
setToken(getToken())

// simple retry mechanism
const DEFAULT_RETRY = 2

function sleep(ms){ return new Promise(r => setTimeout(r, ms)) }

api.interceptors.request.use(cfg => {
  // ensure Authorization header present if token stored
  const t = getToken()
  if (t && !cfg.headers?.Authorization) cfg.headers.Authorization = `Bearer ${t}`
  cfg._retryCount = cfg._retryCount || 0
  return cfg
})

api.interceptors.response.use(
  res => res,
  async err => {
    const cfg = err.config
    if (!cfg) return Promise.reject(err)

    const status = err.response?.status
    const shouldRetry = (status === 429 || (status >= 500 && status < 600) || !err.response)
    const max = cfg.__retry || DEFAULT_RETRY

    if (shouldRetry && cfg._retryCount < max) {
      cfg._retryCount = (cfg._retryCount || 0) + 1
      const delay = 300 * Math.pow(2, cfg._retryCount)
      await sleep(delay)
      return api(cfg)
    }

    // for 401 we keep default behavior (caller can handle)
    return Promise.reject(err)
  }
)

export default api
