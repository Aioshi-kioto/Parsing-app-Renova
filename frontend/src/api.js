/**
 * Renova Parse CRM - API Client
 * Port from VITE_API_PORT (set by start.py) or default 8000
 */
const API_PORT = import.meta.env.VITE_API_PORT || '8000'
const API_BASE = `http://localhost:${API_PORT}/api`

// ================================
// ОБЩИЕ ФУНКЦИИ
// ================================

async function fetchApi(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  
  return response.json()
}

// ================================
// ANALYTICS API
// ================================

export async function getOverviewStats() {
  return fetchApi('/analytics/overview')
}

// Zillow Analytics
export async function getZillowPriceDistribution(jobId = null, bins = 10) {
  const params = new URLSearchParams({ bins })
  if (jobId) params.append('job_id', jobId)
  return fetchApi(`/analytics/zillow/price-distribution?${params}`)
}

export async function getZillowTimeline(days = 30, jobId = null) {
  const params = new URLSearchParams({ days })
  if (jobId) params.append('job_id', jobId)
  return fetchApi(`/analytics/zillow/timeline?${params}`)
}

export async function getZillowByCity(limit = 10, jobId = null) {
  const params = new URLSearchParams({ limit })
  if (jobId) params.append('job_id', jobId)
  return fetchApi(`/analytics/zillow/by-city?${params}`)
}

export async function getZillowHomeTypes(jobId = null) {
  const params = jobId ? `?job_id=${jobId}` : ''
  return fetchApi(`/analytics/zillow/home-types${params}`)
}

// Permits Analytics
export async function getPermitsCostDistribution(jobId = null, bins = 10) {
  const params = new URLSearchParams({ bins })
  if (jobId) params.append('job_id', jobId)
  return fetchApi(`/analytics/permits/cost-distribution?${params}`)
}

export async function getPermitsTimeline(days = 90, jobId = null) {
  const params = new URLSearchParams({ days })
  if (jobId) params.append('job_id', jobId)
  return fetchApi(`/analytics/permits/timeline?${params}`)
}

export async function getOwnerBuilderRatio(jobId = null) {
  const params = jobId ? `?job_id=${jobId}` : ''
  return fetchApi(`/analytics/permits/owner-builder-ratio${params}`)
}

export async function getPermitsByClass(jobId = null) {
  const params = jobId ? `?job_id=${jobId}` : ''
  return fetchApi(`/analytics/permits/by-permit-class${params}`)
}

// Map Data
export async function getMapZillowHomes(jobId = null, limit = 500) {
  const params = new URLSearchParams({ limit })
  if (jobId) params.append('job_id', jobId)
  return fetchApi(`/analytics/map/zillow?${params}`)
}

export async function getMapPermits(jobId = null, isOwnerBuilder = null, limit = 500) {
  const params = new URLSearchParams({ limit })
  if (jobId) params.append('job_id', jobId)
  if (isOwnerBuilder !== null) params.append('is_owner_builder', isOwnerBuilder)
  return fetchApi(`/analytics/map/permits?${params}`)
}

export async function getMapCombined(limit = 500) {
  return fetchApi(`/analytics/map/combined?limit=${limit}`)
}

// ================================
// ZILLOW API
// ================================

export async function startZillowParse(urls) {
  return fetchApi('/zillow/parse', {
    method: 'POST',
    body: JSON.stringify({ urls })
  })
}

export async function getZillowStatus(jobId) {
  return fetchApi(`/zillow/status/${jobId}`)
}

export async function getZillowJobs(limit = 100) {
  return fetchApi(`/zillow/jobs?limit=${limit}`)
}

export async function getZillowHomes(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/zillow/homes?${searchParams}`)
}

export async function getZillowStats(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/zillow/stats?${searchParams}`)
}

export function getZillowExportUrl(jobId, format = 'csv') {
  return `${API_BASE}/zillow/export/${jobId}?format=${format}`
}

export function getZillowExportAllUrl(params = {}) {
  const searchParams = new URLSearchParams({ format: 'csv', ...params })
  return `${API_BASE}/zillow/export?${searchParams}`
}

// ================================
// PERMITS API
// ================================

export async function startPermitParse(config) {
  return fetchApi('/permits/parse', {
    method: 'POST',
    body: JSON.stringify(config)
  })
}

export async function getPermitStatus(jobId) {
  return fetchApi(`/permits/status/${jobId}`)
}

export async function getPermitJobs(limit = 100) {
  return fetchApi(`/permits/jobs?limit=${limit}`)
}

export async function getPermits(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/permits/list?${searchParams}`)
}

export async function getPermitStats(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/permits/stats?${searchParams}`)
}

export async function getOwnerBuilders(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/permits/owner-builders?${searchParams}`)
}

export function getPermitExportUrl(jobId, format = 'csv', onlyOwners = false) {
  return `${API_BASE}/permits/export/${jobId}?format=${format}&only_owners=${onlyOwners}`
}

export function getPermitExportAllUrl(params = {}) {
  const searchParams = new URLSearchParams({ format: 'csv', ...params })
  return `${API_BASE}/permits/export?${searchParams}`
}

// ================================
// LEGACY COMPATIBILITY (for existing components)
// ================================

// Aliases for backward compatibility
export const startParse = startZillowParse
export const getStatus = getZillowStatus
export const getJobs = getZillowJobs
export const getAllHomes = getZillowHomes
export const getHomesStats = getZillowStats
