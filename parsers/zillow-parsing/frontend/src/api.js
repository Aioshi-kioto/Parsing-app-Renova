const API_BASE = '/api'

export async function startParse(urls) {
  const response = await fetch(`${API_BASE}/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urls })
  })
  if (!response.ok) throw new Error('Ошибка запуска парсинга')
  return response.json()
}

export async function getStatus(jobId) {
  const response = await fetch(`${API_BASE}/status/${jobId}`)
  if (!response.ok) throw new Error('Ошибка получения статуса')
  return response.json()
}

export async function getJobs() {
  const response = await fetch(`${API_BASE}/jobs`)
  if (!response.ok) throw new Error('Ошибка получения списка')
  return response.json()
}

export async function getHomes(jobId, skip = 0, limit = 100) {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/homes?skip=${skip}&limit=${limit}`)
  if (!response.ok) throw new Error('Ошибка получения домов')
  return response.json()
}

export function getExportUrl(jobId, format = 'csv') {
  return `${API_BASE}/jobs/${jobId}/export?format=${format}`
}

export async function getAllHomes(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== '')
  )
  const q = new URLSearchParams(clean).toString()
  const url = q ? `${API_BASE}/homes?${q}` : `${API_BASE}/homes`
  const response = await fetch(url)
  if (!response.ok) throw new Error('Ошибка загрузки данных')
  return response.json()
}

export async function getHomesStats(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== '')
  )
  const q = new URLSearchParams(clean).toString()
  const url = q ? `${API_BASE}/homes/stats?${q}` : `${API_BASE}/homes/stats`
  const response = await fetch(url)
  if (!response.ok) throw new Error('Ошибка загрузки статистики')
  return response.json()
}
