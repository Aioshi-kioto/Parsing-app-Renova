/**
 * Renova Parse CRM - API Client
 * Uses Vite proxy for API calls (configured in vite.config.js)
 */
import { getMockExportUrl, isMockMode, mockFetchApi } from './mocks/mockApi'

const API_BASE = '/api'
const USE_MOCK_API = isMockMode
const ENABLE_MOCK_FALLBACK = import.meta.env.VITE_MOCK_FALLBACK !== 'false'

// ================================
// ОБЩИЕ ФУНКЦИИ
// ================================

async function fetchApi(endpoint, options = {}) {
  if (USE_MOCK_API) {
    return mockFetchApi(endpoint, options)
  }

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
    if (ENABLE_MOCK_FALLBACK && error instanceof TypeError && error.message.includes('fetch')) {
      return mockFetchApi(endpoint, options)
    }
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Network error: Unable to connect to API. Please ensure the backend is running on the correct port.')
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
  if (USE_MOCK_API) return getMockExportUrl('zillow')
  return `${API_BASE}/zillow/export/${jobId}?format=${format}`
}

export function getZillowExportAllUrl(params = {}) {
  if (USE_MOCK_API) return getMockExportUrl('zillow')
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
  if (USE_MOCK_API) return getMockExportUrl('permits')
  return `${API_BASE}/permits/export/${jobId}?format=${format}&only_owners=${onlyOwners}`
}

export function getPermitExportAllUrl(params = {}) {
  if (USE_MOCK_API) return getMockExportUrl('permits')
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
  if (USE_MOCK_API) return getMockExportUrl('mbp')
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
// LEADS / TASKS API (Sprint 1)
// ================================

export async function getLeads(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/leads?${searchParams}`)
}

export async function getLeadStats() {
  return fetchApi('/leads/stats')
}

export async function getPendingReviewLeads() {
  return fetchApi('/leads/pending-review')
}

export async function updateLeadStatus(leadId, status) {
  return fetchApi(`/leads/${leadId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status })
  })
}

export async function updateLeadNotes(leadId, notes) {
  return fetchApi(`/leads/${leadId}/notes`, {
    method: 'PATCH',
    body: JSON.stringify({ notes })
  })
}

export async function approveLead(leadId, approvedBy = 'admin', reason = '') {
  return fetchApi(`/leads/${leadId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved_by: approvedBy, reason })
  })
}

export async function getTasksToday() {
  return fetchApi('/tasks/today')
}

export async function snoozeTask(leadId, hours = 24) {
  return fetchApi(`/tasks/${leadId}/snooze`, {
    method: 'POST',
    body: JSON.stringify({ hours })
  })
}

export async function sendTelegramTest() {
  return fetchApi('/telegram/test', { method: 'POST' })
}

// ================================
// DASHBOARD OPERATIONS API
// ================================

export async function getDashboardOperations() {
  return fetchApi('/dashboard/operations')
}

// ================================
// JOBS API (unified)
// ================================

export async function getJobsList(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/jobs?${searchParams}`)
}

export async function getJobDetail(jobId, parserType = null) {
  const params = parserType ? `?parser_type=${encodeURIComponent(parserType)}` : ''
  return fetchApi(`/jobs/${jobId}${params}`)
}

// ================================
// PARSER SETTINGS API
// ================================

export async function getParserSettings(parserType) {
  return fetchApi(`/parser-settings/${parserType}`)
}

export async function updateParserSettings(parserType, payload) {
  return fetchApi(`/parser-settings/${parserType}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export async function applyParserSettingsToNextJobs(payload) {
  return fetchApi('/parser-settings/apply-to-next', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

// ================================
// SCHEDULED OPERATIONS API
// ================================

export async function getScheduledOperations(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value)
    }
  })
  return fetchApi(`/scheduled-operations?${searchParams}`)
}

export async function createScheduledOperation(payload) {
  return fetchApi('/scheduled-operations', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function cancelScheduledOperation(opId, payload = {}) {
  return fetchApi(`/scheduled-operations/${opId}/cancel`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function runScheduledOperationNow(opId) {
  return fetchApi(`/scheduled-operations/${opId}/run-now`, {
    method: 'POST'
  })
}

export async function updateScheduledOperation(opId, payload) {
  return fetchApi(`/scheduled-operations/${opId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })
}

// ================================
// PROVIDER COSTS API
// ================================

export async function getProviderCostsSummary() {
  return fetchApi('/provider-costs/summary')
}

export async function getProviderPolicies() {
  return fetchApi('/provider-costs/policies')
}

export async function updateProviderPolicy(provider, payload) {
  return fetchApi(`/provider-costs/policies/${provider}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export async function getProviderBudgets() {
  return fetchApi('/provider-costs/budgets')
}

export async function updateProviderBudget(provider, payload) {
  return fetchApi(`/provider-costs/budgets/${provider}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

// ================================
// OUTBOUND TEMPLATES API
// ================================

export async function getOutboundTemplates() {
  return fetchApi('/outbound/templates')
}

export async function getOutboundTemplate(caseCode) {
  return fetchApi(`/outbound/templates/${caseCode}`)
}

export async function updateOutboundTemplate(caseCode, payload) {
  return fetchApi(`/outbound/templates/${caseCode}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export async function sendOutboundTestEmail(payload) {
  return fetchApi('/outbound/test-email', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function sendOutboundTestLob(payload) {
  return fetchApi('/outbound/test-lob', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

// ================================
// ANALYTICS LEADS API
// ================================

export async function getLeadsByCase() {
  return fetchApi('/analytics/leads/by-case')
}

export async function getLeadsByPriority() {
  return fetchApi('/analytics/leads/by-priority')
}

export async function getLeadsByStatus() {
  return fetchApi('/analytics/leads/by-status')
}


export async function getOutboundStats() {
  return fetchApi('/analytics/outbound/stats')
}

export async function getBillingStats() {
  return fetchApi('/analytics/billing')
}

// ================================
// SIMULATION API
// ================================

export async function runSimulation(config = {}) {
  return fetchApi('/simulation/run', {
    method: 'POST',
    body: JSON.stringify(config)
  })
}

export async function getSimulationStatus(simId) {
  return fetchApi(`/simulation/status/${simId}`)
}

// ================================
// LEGACY COMPATIBILITY (for existing components)
// ================================

export const startParse = startZillowParse
export const getStatus = getZillowStatus
export const getJobs = getZillowJobs
export const getAllHomes = getZillowHomes
export const getHomesStats = getZillowStats
