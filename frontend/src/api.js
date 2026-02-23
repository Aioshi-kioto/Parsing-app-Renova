/**
 * Renova Parse CRM - API Client
 * Uses Vite proxy for API calls (configured in vite.config.js)
 */
const API_BASE = '/api'

// ================================
// ОБЩИЕ ФУНКЦИИ
// ================================

async function fetchApi(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`

  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}: ${response.statusText}` }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  } catch (error) {
    // Enhanced error handling for network issues
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error(`Network error: Unable to connect to API. Please ensure the backend is running on the correct port.`)
    }
    throw error
  }
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

export async function startZillowParse(urls, headless = false) {
  return fetchApi('/zillow/parse', {
    method: 'POST',
    body: JSON.stringify({ urls, headless })
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
// MYBUILDINGPERMIT API
// ================================

export async function getMBPJurisdictions() {
  return fetchApi('/mybuildingpermit/jurisdictions')
}

export async function startMBPParse(config) {
  return fetchApi('/mybuildingpermit/parse', {
    method: 'POST',
    body: JSON.stringify(config)
  })
}

export async function getMBPStatus(jobId) {
  return fetchApi(`/mybuildingpermit/status/${jobId}`)
}

export async function getMBPJobs(limit = 100) {
  return fetchApi(`/mybuildingpermit/jobs?limit=${limit}`)
}

export async function getMBPPermits(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/mybuildingpermit/list?${searchParams}`)
}

export async function getMBPStats(jobId = null) {
  const params = jobId ? `?job_id=${jobId}` : ''
  return fetchApi(`/mybuildingpermit/stats${params}`)
}

export async function getMBPOwnerBuilders(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/mybuildingpermit/owner-builders?${searchParams}`)
}

export function getMBPExportUrl(jobId = null, format = 'csv', onlyOwners = false) {
  const params = new URLSearchParams({ format, only_owners: onlyOwners })
  if (jobId) params.append('job_id', jobId)
  return `${API_BASE}/mybuildingpermit/export?${params}`
}

export async function cancelMBPJob(jobId) {
  return fetchApi(`/mybuildingpermit/jobs/${jobId}/cancel`, {
    method: 'POST'
  })
}

export async function deleteMBPJob(jobId) {
  return fetchApi(`/mybuildingpermit/jobs/${jobId}`, {
    method: 'DELETE'
  })
}

// ================================
// PERMITS CANCEL / DELETE
// ================================

export async function cancelPermitJob(jobId) {
  return fetchApi(`/permits/jobs/${jobId}/cancel`, {
    method: 'POST'
  })
}

export async function deletePermitJob(jobId) {
  return fetchApi(`/permits/jobs/${jobId}`, {
    method: 'DELETE'
  })
}

// ================================
// ZILLOW CANCEL / DELETE
// ================================

export async function cancelZillowJob(jobId) {
  return fetchApi(`/zillow/jobs/${jobId}/cancel`, {
    method: 'POST'
  })
}

export async function deleteZillowJob(jobId) {
  return fetchApi(`/zillow/jobs/${jobId}`, {
    method: 'DELETE'
  })
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
