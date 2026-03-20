import {
  billing,
  dashboardAlerts,
  jobs,
  leads,
  mbpJurisdictions,
  mbpPermits,
  permitsList,
  scheduler,
  simulationStatus,
  zillowHomes,
} from './data'

const MOCK_DELAY_MS = Number(import.meta.env.VITE_MOCK_DELAY_MS || 140)
export const isMockMode = import.meta.env.VITE_USE_MOCKS !== 'false'

let zillowJobs = [...jobs.zillow]
let permitJobs = [...jobs.permits]
let mbpJobs = [...jobs.mbp]
let leadRows = [...leads]
let outboundTemplates = [
  { case_type: 'GENERAL', email_subject: 'Ваш строительный проект на {street_name}', email_body: 'Привет {owner_name},\n\nТестовый шаблон GENERAL.\n\n— Renova', sms_body: 'Renova: проект на {street_name}.', lob_template_id: null, lob_body_html: null },
  { case_type: 'PERMIT_SNIPER', email_subject: 'Ваш проект на {street_name} / Renova', email_body: 'Привет {owner_name},\n\nТестовый шаблон PERMIT_SNIPER.\n\n— Renova', sms_body: 'Renova: проект на {street_name}.', lob_template_id: null, lob_body_html: null },
]

let zillowJobSeq = Math.max(...zillowJobs.map((j) => j.id), 400)
let permitJobSeq = Math.max(...permitJobs.map((j) => j.id), 500)
let mbpJobSeq = Math.max(...mbpJobs.map((j) => j.id), 600)

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const toIso = () => new Date().toISOString()

function parseUrl(endpoint) {
  const [path, queryString = ''] = endpoint.split('?')
  return { path, params: new URLSearchParams(queryString) }
}

function toNumber(value, fallback = 0) {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function matchText(value, query) {
  if (!query) return true
  return String(value || '').toLowerCase().includes(String(query).toLowerCase())
}

function applyPagination(list, params) {
  const skip = toNumber(params.get('skip'), 0)
  const limit = toNumber(params.get('limit'), list.length || 50)
  return {
    total: list.length,
    list: list.slice(skip, skip + limit),
  }
}

function getUnifiedJobs() {
  return [...zillowJobs, ...permitJobs, ...mbpJobs]
    .map((job) => {
      const startedAt = job.started_at || null
      const finishedAt = job.completed_at || job.finished_at || null
      const progress = computeProgress(job)
      return {
        ...job,
        started_at: startedAt,
        finished_at: finishedAt,
        scheduled_at: job.scheduled_at || null,
        progress,
        duration: startedAt ? computeDuration(startedAt, finishedAt) : '--',
        result_summary: computeResultSummary(job),
        log: startedAt ? `INFO: ${job.type} job #${job.id}\nSTATUS: ${job.status}\nStarted: ${startedAt}` : null,
        error: job.error_message || null,
        parser_name: parserLabel(job.type),
        subprocesses: job.subprocesses || [],
        config: job.config || {},
        result: job.result || {},
      }
    })
    .sort((a, b) => {
      const aTime = a.scheduled_at || a.started_at || ''
      const bTime = b.scheduled_at || b.started_at || ''
      return new Date(bTime).getTime() - new Date(aTime).getTime()
    })
}

function parserLabel(type) {
  if (type === 'permits') return 'Пермит'
  if (type === 'mbp') return 'MyBuilding'
  return 'Парсер'
}

function computeDuration(startedAt, finishedAt) {
  if (!startedAt) return '--'
  const start = new Date(startedAt).getTime()
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now()
  const sec = Math.max(1, Math.round((end - start) / 1000))
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  const rem = sec % 60
  return rem ? `${min}m ${rem}s` : `${min}m`
}

function computeProgress(job) {
  if (job.status === 'completed') return 100
  if (job.status === 'failed' || job.status === 'cancelled') return 100
  if (job.type === 'zillow' && job.total_urls) return Math.round(((job.current_url_index || 0) + 1) / job.total_urls * 100)
  if (job.type === 'permits' && job.permits_found) return Math.round((job.permits_verified || 0) / job.permits_found * 100)
  if (job.type === 'mbp' && job.total_permits) return Math.round((job.analyzed_count || 0) / job.total_permits * 100)
  return 30
}

function computeResultSummary(job) {
  if (job.type === 'permits') return `${job.owner_builders_found || 0} собств.-застр.`
  if (job.type === 'mbp') return `${job.owner_builders_found || 0} собств.-застр.`
  return '—'
}

function maybeAdvanceZillowStatus(job) {
  if (!job || job.status !== 'running') return job
  if ((job.current_url_index || 0) < (job.total_urls || 1) - 1) {
    job.current_url_index += 1
    job.homes_found += 8
    job.unique_homes += 6
  } else {
    job.status = 'completed'
    job.completed_at = toIso()
  }
  return job
}

function maybeAdvancePermitStatus(job) {
  if (!job || !['running', 'fetching', 'processing', 'verifying', 'pending'].includes(job.status)) return job
  job.status = 'verifying'
  if ((job.permits_verified || 0) < (job.permits_found || 1)) {
    job.permits_verified += 4
    job.owner_builders_found = Math.max(job.owner_builders_found || 0, Math.round(job.permits_verified * 0.45))
  }
  if (job.permits_verified >= job.permits_found) {
    job.permits_verified = job.permits_found
    job.status = 'completed'
    job.completed_at = toIso()
  }
  return job
}

function maybeAdvanceMBPStatus(job) {
  if (!job || !['running', 'pending'].includes(job.status)) return job
  if ((job.analyzed_count || 0) < (job.total_permits || 1)) {
    job.analyzed_count += 2
    job.elapsed_seconds += 7
  }
  if (job.analyzed_count >= job.total_permits) {
    job.analyzed_count = job.total_permits
    job.status = 'completed'
    job.completed_at = toIso()
  }
  return job
}

function leadsByCase() {
  const grouped = {}
  leadRows.forEach((row) => {
    grouped[row.case_type] = (grouped[row.case_type] || 0) + 1
  })
  return Object.entries(grouped).map(([case_type, count]) => ({ case_type, count }))
}

function leadsByPriority() {
  const grouped = { RED: 0, YELLOW: 0, GREEN: 0 }
  leadRows.forEach((row) => {
    grouped[row.priority] = (grouped[row.priority] || 0) + 1
  })
  return grouped
}

function leadsByStatus() {
  const grouped = {}
  leadRows.forEach((row) => {
    grouped[row.status] = (grouped[row.status] || 0) + 1
  })
  return Object.entries(grouped).map(([status, count]) => ({ status, count }))
}

function buildDashboardOperations() {
  const unifiedJobs = getUnifiedJobs()
  const activeJobs = unifiedJobs.filter((job) => ['running', 'pending', 'queued', 'parsing', 'verifying'].includes(job.status)).length
  return {
    active_jobs: activeJobs,
    total_leads: leadRows.length,
    leads_last_week: 3,
    outbound_today: 11,
    errors_24h: unifiedJobs.filter((job) => job.status === 'failed').length,
    batchdata_used: billing.batchdata.success_count,
    batchdata_limit: 2000,
    recent_alerts: dashboardAlerts,
    scheduler,
  }
}

function buildOverviewStats() {
  return {
    permits: {
      total_permits: permitsList.length,
      success_rate: '92%',
      last_parse: permitJobs[0]?.started_at || '--',
      last_status: permitJobs[0]?.status || 'idle',
      total_jobs: permitJobs.length,
    },
    mbp: {
      total_permits: mbpPermits.length,
      success_rate: '86%',
      last_parse: mbpJobs[0]?.started_at || '--',
      last_status: mbpJobs[0]?.status || 'idle',
      total_jobs: mbpJobs.length,
    },
    zillow: {
      total_homes: zillowHomes.length,
      success_rate: '88%',
      last_parse: zillowJobs[0]?.started_at || '--',
      last_status: zillowJobs[0]?.status || 'idle',
      total_jobs: zillowJobs.length,
    },
  }
}

function buildOutboundStats() {
  return {
    letters_sent: 47,
    emails_sent: 122,
    calls_made: 36,
    response_rate: '14.8%',
    timeline: Array.from({ length: 30 }).map((_, idx) => ({
      label: `${idx + 1}`,
      count: (idx % 6) + 1 + (idx > 25 ? 3 : 0),
    })),
  }
}

function buildPermitStats() {
  const total = permitsList.length
  const ownerBuilders = permitsList.filter((p) => p.is_owner_builder).length
  const totalCost = permitsList.reduce((sum, p) => sum + (p.project_cost || 0), 0)
  return {
    total,
    owner_builders: ownerBuilders,
    avg_cost: total ? totalCost / total : 0,
    total_cost: totalCost,
  }
}

function buildMBPStats() {
  return {
    total: mbpPermits.length,
    owner_builders_from_matching: mbpPermits.filter((p) => p.is_owner_builder).length,
  }
}

function buildCsv(kind) {
  if (kind === 'zillow') {
    return [
      'zpid,address,city,zip_code,price,beds,baths,sqft,home_type',
      ...zillowHomes.map((h) => [h.zpid, h.address, h.city, h.zip_code, h.price, h.beds, h.baths, h.sqft, h.home_type].join(',')),
    ].join('\n')
  }
  if (kind === 'permits') {
    return [
      'permit_number,address,city,project_cost,status,is_owner_builder',
      ...permitsList.map((p) => [p.permit_number, p.address, p.city, p.project_cost, p.status, p.is_owner_builder].join(',')),
    ].join('\n')
  }
  if (kind === 'mbp') {
    return [
      'permit_number,jurisdiction,address,permit_type,status,is_owner_builder',
      ...mbpPermits.map((p) => [p.permit_number, p.jurisdiction, p.address, p.permit_type, p.status, p.is_owner_builder].join(',')),
    ].join('\n')
  }
  return 'id\n1'
}

export function getMockExportUrl(kind) {
  const csv = buildCsv(kind)
  return `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`
}

export async function mockFetchApi(endpoint, options = {}) {
  await sleep(MOCK_DELAY_MS)

  const method = (options.method || 'GET').toUpperCase()
  const body = options.body ? JSON.parse(options.body) : null
  const { path, params } = parseUrl(endpoint)

  if (path === '/dashboard/operations') return buildDashboardOperations()
  if (path === '/analytics/overview') return buildOverviewStats()
  if (path === '/analytics/leads/by-case') return { cases: leadsByCase() }
  if (path === '/analytics/leads/by-priority') return { priorities: leadsByPriority() }
  if (path === '/analytics/leads/by-status') return { statuses: leadsByStatus() }
  if (path === '/analytics/outbound/stats') return buildOutboundStats()
  if (path === '/analytics/billing') return billing
  if (path === '/simulation/run' && method === 'POST') return simulationStatus
  if (path.startsWith('/simulation/status/')) return simulationStatus

  if (path === '/jobs') {
    const list = getUnifiedJobs()
    const limit = toNumber(params.get('limit'), 100)
    return { jobs: list.slice(0, limit) }
  }
  if (path.startsWith('/jobs/')) {
    const jobId = toNumber(path.split('/')[2])
    return getUnifiedJobs().find((job) => job.id === jobId) || null
  }

  if (path === '/outbound/templates') {
    return { templates: [...outboundTemplates] }
  }
  if (path.startsWith('/outbound/templates/') && method === 'GET') {
    const caseType = decodeURIComponent(path.split('/')[3] || 'GENERAL')
    const row = outboundTemplates.find((t) => t.case_type === caseType) || outboundTemplates[0]
    return row || null
  }
  if (path.startsWith('/outbound/templates/') && method === 'PUT') {
    const caseType = decodeURIComponent(path.split('/')[3] || 'GENERAL')
    const payload = {
      case_type: caseType,
      email_subject: body?.email_subject || '',
      email_body: body?.email_body || '',
      sms_body: body?.sms_body || '',
      lob_template_id: body?.lob_template_id || null,
      lob_body_html: body?.lob_body_html || null,
    }
    const idx = outboundTemplates.findIndex((t) => t.case_type === caseType)
    if (idx >= 0) outboundTemplates[idx] = payload
    else outboundTemplates.push(payload)
    return { ok: true, template: payload }
  }
  if (path === '/outbound/test-email' && method === 'POST') {
    return { ok: true, message_id: 'mock_sendgrid_id' }
  }
  if (path === '/outbound/test-lob' && method === 'POST') {
    return { ok: true, lob_id: 'mock_lob_id_12345' }
  }

  if (path === '/zillow/parse' && method === 'POST') {
    zillowJobSeq += 1
    const totalUrls = Array.isArray(body?.urls) ? body.urls.length : 1
    zillowJobs.unshift({
      id: zillowJobSeq,
      type: 'zillow',
      status: 'running',
      total_urls: Math.max(1, totalUrls),
      current_url_index: 0,
      homes_found: 2,
      unique_homes: 2,
      started_at: toIso(),
      completed_at: null,
      error_message: null,
      config: { mode: 'URL list', urls_count: totalUrls, headless: !!body?.headless },
      result: { records_total: 0, records_unique: 0, duration_seconds: 0 },
      subprocesses: [{ id: `sp-${zillowJobSeq}-1`, stage_key: 'enrichment', title: 'Обогащение контактов', status: 'pending', started_at: null, completed_at: null, result: 'Ожидание завершения парсера' }],
    })
    return { job_id: zillowJobSeq }
  }
  if (path.startsWith('/zillow/status/')) {
    const jobId = toNumber(path.split('/')[3])
    const job = zillowJobs.find((item) => item.id === jobId)
    maybeAdvanceZillowStatus(job)
    return job || { detail: 'Not found' }
  }
  if (path === '/zillow/jobs') {
    const limit = toNumber(params.get('limit'), 100)
    return zillowJobs.slice(0, limit)
  }
  if (path.startsWith('/zillow/jobs/') && path.endsWith('/cancel') && method === 'POST') {
    const jobId = toNumber(path.split('/')[3])
    zillowJobs = zillowJobs.map((job) => (job.id === jobId ? { ...job, status: 'cancelled', completed_at: toIso() } : job))
    return { ok: true }
  }
  if (path.startsWith('/zillow/jobs/') && method === 'DELETE') {
    const jobId = toNumber(path.split('/')[3])
    zillowJobs = zillowJobs.filter((job) => job.id !== jobId)
    return { ok: true }
  }
  if (path === '/zillow/homes') {
    let list = [...zillowHomes]
    const search = params.get('search')
    const city = params.get('city')
    const min = toNumber(params.get('min_price'), 0)
    const max = toNumber(params.get('max_price'), Number.MAX_SAFE_INTEGER)
    list = list.filter((row) => matchText(row.address, search) || matchText(row.zpid, search))
    if (city) list = list.filter((row) => matchText(row.city, city))
    list = list.filter((row) => (row.price || 0) >= min && (row.price || 0) <= max)
    const paged = applyPagination(list, params)
    return { homes: paged.list, total: paged.total }
  }
  if (path === '/zillow/stats') {
    return {
      total: zillowHomes.length,
      avg_price: zillowHomes.reduce((sum, row) => sum + row.price, 0) / zillowHomes.length,
      by_city: [{ city: 'Seattle', count: zillowHomes.length }],
    }
  }

  if (path === '/permits/parse' && method === 'POST') {
    permitJobSeq += 1
    permitJobs.unshift({
      id: permitJobSeq,
      type: 'permits',
      status: 'verifying',
      year: body?.year || 2026,
      permits_found: 24,
      permits_verified: 4,
      owner_builders_found: 2,
      started_at: toIso(),
      completed_at: null,
      error_message: null,
      config: { year: body?.year || 2026, permit_class: body?.permit_class || 'Single Family / Duplex', min_cost: body?.min_cost || 5000, owner_builder_check: !!body?.verify_owner_builder },
      result: { permits_found: 24, owner_builder_matches: 2, duration_seconds: 0 },
      subprocesses: [{ id: `sp-${permitJobSeq}-1`, stage_key: 'enrichment', title: 'Обогащение контактов', status: 'pending', started_at: null, completed_at: null, result: 'Ожидание завершения парсера' }],
    })
    return { job_id: permitJobSeq }
  }
  if (path.startsWith('/permits/status/')) {
    const jobId = toNumber(path.split('/')[3])
    const job = permitJobs.find((item) => item.id === jobId)
    maybeAdvancePermitStatus(job)
    return job || { detail: 'Not found' }
  }
  if (path === '/permits/jobs') {
    const limit = toNumber(params.get('limit'), 100)
    return permitJobs.slice(0, limit)
  }
  if (path.startsWith('/permits/jobs/') && path.endsWith('/cancel') && method === 'POST') {
    const jobId = toNumber(path.split('/')[3])
    permitJobs = permitJobs.map((job) => (job.id === jobId ? { ...job, status: 'cancelled', completed_at: toIso() } : job))
    return { ok: true }
  }
  if (path.startsWith('/permits/jobs/') && method === 'DELETE') {
    const jobId = toNumber(path.split('/')[3])
    permitJobs = permitJobs.filter((job) => job.id !== jobId)
    return { ok: true }
  }
  if (path === '/permits/stats') return buildPermitStats()
  if (path === '/permits/owner-builders') {
    const list = permitsList.filter((row) => row.is_owner_builder)
    const limit = toNumber(params.get('limit'), list.length)
    return { permits: list.slice(0, limit), total: list.length }
  }
  if (path === '/permits/list') {
    let list = [...permitsList]
    const search = params.get('search')
    const city = params.get('city')
    const min = toNumber(params.get('min_cost'), 0)
    const max = toNumber(params.get('max_cost'), Number.MAX_SAFE_INTEGER)
    const ob = params.get('is_owner_builder')
    list = list.filter((row) => matchText(row.address, search) || matchText(row.permit_number, search))
    if (city) list = list.filter((row) => matchText(row.city, city))
    list = list.filter((row) => (row.project_cost || 0) >= min && (row.project_cost || 0) <= max)
    if (ob === 'true') list = list.filter((row) => row.is_owner_builder)
    if (ob === 'false') list = list.filter((row) => !row.is_owner_builder)
    const paged = applyPagination(list, params)
    return { permits: paged.list, total: paged.total }
  }

  if (path === '/mybuildingpermit/jurisdictions') return { jurisdictions: mbpJurisdictions }
  if (path === '/mybuildingpermit/parse' && method === 'POST') {
    mbpJobSeq += 1
    mbpJobs.unshift({
      id: mbpJobSeq,
      type: 'mbp',
      status: 'running',
      jurisdictions: JSON.stringify(body?.jurisdictions || ['Bellevue']),
      date_from_str: '03/15/2026',
      date_to_str: '03/20/2026',
      total_permits: 12,
      analyzed_count: 1,
      owner_builders_found: 0,
      elapsed_seconds: 4,
      current_jurisdiction: (body?.jurisdictions || ['Bellevue'])[0],
      started_at: toIso(),
      completed_at: null,
      error_message: null,
      config: { jurisdictions: body?.jurisdictions || ['Bellevue'], days_back: body?.days_back || 7, browser_visible: !body?.headless },
      result: { permits_found: 12, owner_builder_matches: 0, duration_seconds: 0 },
      subprocesses: [{ id: `sp-${mbpJobSeq}-1`, stage_key: 'enrichment', title: 'Обогащение контактов', status: 'pending', started_at: null, completed_at: null, result: 'Ожидание завершения парсера' }],
    })
    return { job_id: mbpJobSeq }
  }
  if (path.startsWith('/mybuildingpermit/status/')) {
    const jobId = toNumber(path.split('/')[3])
    const job = mbpJobs.find((item) => item.id === jobId)
    maybeAdvanceMBPStatus(job)
    return job || { detail: 'Not found' }
  }
  if (path === '/mybuildingpermit/jobs') {
    const limit = toNumber(params.get('limit'), 100)
    return mbpJobs.slice(0, limit)
  }
  if (path.startsWith('/mybuildingpermit/jobs/') && path.endsWith('/cancel') && method === 'POST') {
    const jobId = toNumber(path.split('/')[3])
    mbpJobs = mbpJobs.map((job) => (job.id === jobId ? { ...job, status: 'cancelled', completed_at: toIso() } : job))
    return { ok: true }
  }
  if (path.startsWith('/mybuildingpermit/jobs/') && method === 'DELETE') {
    const jobId = toNumber(path.split('/')[3])
    mbpJobs = mbpJobs.filter((job) => job.id !== jobId)
    return { ok: true }
  }
  if (path === '/mybuildingpermit/stats') return buildMBPStats()
  if (path === '/mybuildingpermit/owner-builders') {
    const list = mbpPermits.filter((row) => row.is_owner_builder)
    const limit = toNumber(params.get('limit'), list.length)
    return { permits: list.slice(0, limit), total: list.length }
  }
  if (path === '/mybuildingpermit/list') {
    let list = [...mbpPermits]
    const search = params.get('search')
    const jurisdiction = params.get('jurisdiction')
    const ob = params.get('is_owner_builder')
    list = list.filter((row) => matchText(row.address, search) || matchText(row.permit_number, search))
    if (jurisdiction) list = list.filter((row) => matchText(row.jurisdiction, jurisdiction))
    if (ob === 'true') list = list.filter((row) => row.is_owner_builder)
    if (ob === 'false') list = list.filter((row) => !row.is_owner_builder)
    const paged = applyPagination(list, params)
    return { permits: paged.list, total: paged.total }
  }

  if (path === '/leads') {
    let list = [...leadRows]
    const search = params.get('search')
    const caseType = params.get('case_type')
    const priority = params.get('priority')
    const status = params.get('status')
    if (search) list = list.filter((row) => matchText(row.address, search) || matchText(row.contact_name, search))
    if (caseType) list = list.filter((row) => row.case_type === caseType)
    if (priority) list = list.filter((row) => row.priority === priority)
    if (status) list = list.filter((row) => row.status === status)
    const paged = applyPagination(list, params)
    return { leads: paged.list, total: paged.total }
  }
  if (path === '/leads/stats') return { total: leadRows.length }
  if (path === '/leads/pending-review') return leadRows.filter((row) => row.status === 'pending_review')
  if (path.startsWith('/leads/') && path.endsWith('/status') && method === 'PATCH') {
    const leadId = path.split('/')[2]
    leadRows = leadRows.map((row) => (row.id === leadId ? { ...row, status: body?.status || row.status } : row))
    return { ok: true }
  }
  if (path.startsWith('/leads/') && path.endsWith('/approve') && method === 'POST') {
    const leadId = path.split('/')[2]
    leadRows = leadRows.map((row) => (row.id === leadId ? { ...row, status: 'approved', is_approved: true } : row))
    return { ok: true }
  }
  if (path.startsWith('/leads/') && path.endsWith('/notes') && method === 'PATCH') {
    return { ok: true }
  }

  if (path === '/tasks/today') {
    return leadRows.filter((row) => !['closed', 'contacted'].includes(row.status)).slice(0, 10)
  }
  if (path.startsWith('/tasks/') && path.endsWith('/snooze') && method === 'POST') {
    const leadId = path.split('/')[2]
    const hours = toNumber(body?.hours, 24)
    leadRows = leadRows.map((row) => {
      if (row.id !== leadId) return row
      const due = row.call_due_at ? new Date(row.call_due_at).getTime() : Date.now()
      return { ...row, call_due_at: new Date(due + hours * 60 * 60 * 1000).toISOString() }
    })
    return { ok: true }
  }
  if (path === '/telegram/test' && method === 'POST') {
    return { ok: true, detail: 'Telegram test mock sent.' }
  }

  if (path.startsWith('/analytics/map/')) {
    return { points: [] }
  }
  if (path === '/analytics/zillow/price-distribution') {
    return { bins: [{ min: 600000, max: 800000, count: 2 }, { min: 800000, max: 1200000, count: 3 }] }
  }
  if (path === '/analytics/zillow/timeline') {
    return { timeline: [{ date: '2026-03-10', count: 2 }, { date: '2026-03-11', count: 1 }] }
  }
  if (path === '/analytics/zillow/by-city') {
    return { cities: [{ city: 'Seattle', count: 5 }] }
  }
  if (path === '/analytics/zillow/home-types') {
    return { home_types: [{ home_type: 'Single Family', count: 3 }, { home_type: 'Townhouse', count: 1 }, { home_type: 'Condo', count: 1 }] }
  }
  if (path === '/analytics/permits/cost-distribution') {
    return { bins: [{ min: 0, max: 10000, count: 1 }, { min: 10000, max: 30000, count: 2 }, { min: 30000, max: 100000, count: 1 }] }
  }
  if (path === '/analytics/permits/timeline') {
    return { timeline: [{ date: '2026-03-08', count: 1 }, { date: '2026-03-09', count: 2 }] }
  }
  if (path === '/analytics/permits/owner-builder-ratio') {
    return { owner_builders: 3, non_owner_builders: 1 }
  }
  if (path === '/analytics/permits/by-permit-class') {
    return { classes: [{ permit_class: 'Single Family / Duplex', count: 4 }] }
  }

  throw new Error(`Mock API: endpoint not implemented (${method} ${path})`)
}
