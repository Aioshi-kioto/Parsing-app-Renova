const now = new Date()

const hoursAgo = (value) => new Date(now.getTime() - value * 60 * 60 * 1000).toISOString()
const daysAgo = (value) => new Date(now.getTime() - value * 24 * 60 * 60 * 1000).toISOString()
const daysFromNow = (value) => new Date(now.getTime() + value * 24 * 60 * 60 * 1000).toISOString()

export const zillowHomes = [
  { id: 1, zpid: '210001001', address: '3951 15th Ave S', city: 'Seattle', zip_code: '98108', price: 865000, beds: 3, baths: 2, sqft: 1820, home_type: 'Single Family', date_sold: '2026-02-20', created_at: daysAgo(20) },
  { id: 2, zpid: '210001002', address: '2518 NW 58th St', city: 'Seattle', zip_code: '98107', price: 1095000, beds: 4, baths: 3, sqft: 2410, home_type: 'Single Family', date_sold: '2026-03-01', created_at: daysAgo(12) },
  { id: 3, zpid: '210001003', address: '6112 39th Ave SW', city: 'Seattle', zip_code: '98136', price: 744000, beds: 2, baths: 1.5, sqft: 1340, home_type: 'Townhouse', date_sold: '2026-02-16', created_at: daysAgo(25) },
  { id: 4, zpid: '210001004', address: '8811 Ashworth Ave N', city: 'Seattle', zip_code: '98103', price: 1275000, beds: 5, baths: 3, sqft: 2980, home_type: 'Single Family', date_sold: '2026-03-10', created_at: daysAgo(3) },
  { id: 5, zpid: '210001005', address: '1466 24th Ave', city: 'Seattle', zip_code: '98122', price: 959000, beds: 3, baths: 2.5, sqft: 1960, home_type: 'Condo', date_sold: '2026-02-28', created_at: daysAgo(9) },
]

export const permitsList = [
  { id: 11, permit_number: '6990011-CN', permit_num: '6990011-CN', address: '3951 15TH AVE S', city: 'Seattle', description: 'Kitchen remodel + panel upgrade', project_cost: 85000, est_project_cost: 85000, permit_class: 'Single Family / Duplex', status: 'Issued', verification_status: 'verified', is_owner_builder: true, applied_date: '2026-03-01', portal_link: 'https://cosaccela.seattle.gov/portal/customization/seattle/home.aspx' },
  { id: 12, permit_number: '6990012-CN', permit_num: '6990012-CN', address: '2208 10TH AVE W', city: 'Seattle', description: 'Roof replacement', project_cost: 27000, est_project_cost: 27000, permit_class: 'Single Family / Duplex', status: 'Issued', verification_status: 'verified', is_owner_builder: true, applied_date: '2026-03-03', portal_link: 'https://cosaccela.seattle.gov/portal/customization/seattle/home.aspx' },
  { id: 13, permit_number: '6990013-CN', permit_num: '6990013-CN', address: '1024 S Orcas St', city: 'Seattle', description: 'Emergency plumbing fix', project_cost: 9200, est_project_cost: 9200, permit_class: 'Single Family / Duplex', status: 'Issued', verification_status: 'pending', is_owner_builder: false, applied_date: '2026-03-06', portal_link: 'https://cosaccela.seattle.gov/portal/customization/seattle/home.aspx' },
  { id: 14, permit_number: '6990014-CN', permit_num: '6990014-CN', address: '7814 Greenwood Ave N', city: 'Seattle', description: 'Electrical rewire', project_cost: 18000, est_project_cost: 18000, permit_class: 'Single Family / Duplex', status: 'Ready to Issue', verification_status: 'verified', is_owner_builder: true, applied_date: '2026-03-08', portal_link: 'https://cosaccela.seattle.gov/portal/customization/seattle/home.aspx' },
]

export const mbpPermits = [
  { id: 31, permit_number: 'B25-009771', jurisdiction: 'Bellevue', address: '1421 154th Ave NE', permit_type: 'Residential Remodel', status: 'Issued', permit_status: 'Issued', applicant_name: 'Alex Lee', permit_url: 'https://permitsearch.mybuildingpermit.com', is_owner_builder: true, created_at: daysAgo(6) },
  { id: 32, permit_number: 'B25-009772', jurisdiction: 'Redmond', address: '8810 Avondale Rd', permit_type: 'Mechanical', status: 'Under Review', permit_status: 'Under Review', applicant_name: 'Renova LLC', permit_url: 'https://permitsearch.mybuildingpermit.com', is_owner_builder: false, created_at: daysAgo(5) },
  { id: 33, permit_number: 'B25-009773', jurisdiction: 'Kirkland', address: '3702 Market St', permit_type: 'Electrical', status: 'Issued', permit_status: 'Issued', applicant_name: 'Daniel Chen', permit_url: 'https://permitsearch.mybuildingpermit.com', is_owner_builder: true, created_at: daysAgo(4) },
]

export const leads = [
  { id: 'lead-1', address: '3951 15TH AVE S, Seattle', case_type: 'PERMIT_SNIPER', priority: 'RED', status: 'pending_review', source: 'sdci', contact_name: 'Young Lee', found_at: hoursAgo(14), call_due_at: hoursAgo(-1), sent_lob_at: null, sent_sendgrid_at: null },
  { id: 'lead-2', address: '2208 10TH AVE W, Seattle', case_type: 'STORM_ROOF_DAMAGE', priority: 'YELLOW', status: 'approved', source: 'mbp', contact_name: 'Julie Evans', found_at: daysAgo(1), call_due_at: hoursAgo(3), sent_lob_at: daysAgo(1), sent_sendgrid_at: null },
  { id: 'lead-3', address: '7814 Greenwood Ave N, Seattle', case_type: 'ELECTRICAL_REWIRE', priority: 'GREEN', status: 'email_sent', source: 'batchdata', contact_name: 'Sam Carter', found_at: daysAgo(2), call_due_at: hoursAgo(6), sent_lob_at: null, sent_sendgrid_at: daysAgo(1) },
  { id: 'lead-4', address: '1466 24th Ave, Seattle', case_type: 'NEW_PURCHASE_HELOC', priority: 'YELLOW', status: 'new', source: 'zillow', contact_name: 'Nina Park', found_at: hoursAgo(9), call_due_at: hoursAgo(12), sent_lob_at: null, sent_sendgrid_at: null },
  { id: 'lead-5', address: '6112 39th Ave SW, Seattle', case_type: 'MECHANICS_LIEN', priority: 'RED', status: 'contacted', source: 'recorder', contact_name: 'Mark Stone', found_at: daysAgo(3), call_due_at: daysAgo(1), sent_lob_at: daysAgo(2), sent_sendgrid_at: daysAgo(2) },
  { id: 'lead-6', address: '1421 154th Ave NE, Bellevue', case_type: 'PERMIT_SNIPER', priority: 'RED', status: 'no_answer', source: 'mbp', contact_name: 'Alex Lee', found_at: hoursAgo(20), call_due_at: hoursAgo(2), sent_lob_at: null, sent_sendgrid_at: null },
  { id: 'lead-7', address: '8810 Avondale Rd, Redmond', case_type: 'STORM_ROOF_DAMAGE', priority: 'GREEN', status: 'letter_sent', source: 'mbp', contact_name: 'Chris Wong', found_at: daysAgo(4), call_due_at: daysAgo(2), sent_lob_at: daysAgo(3), sent_sendgrid_at: null },
  { id: 'lead-8', address: '3702 Market St, Kirkland', case_type: 'ELECTRICAL_REWIRE', priority: 'YELLOW', status: 'pending_review', source: 'mbp', contact_name: 'Daniel Chen', found_at: hoursAgo(6), call_due_at: hoursAgo(4), sent_lob_at: null, sent_sendgrid_at: null },
  { id: 'lead-9', address: '1024 S Orcas St, Seattle', case_type: 'EMERGENCY_PLUMBING', priority: 'RED', status: 'new', source: 'sdci', contact_name: 'Pat Rivera', found_at: hoursAgo(3), call_due_at: hoursAgo(1), sent_lob_at: null, sent_sendgrid_at: null },
  { id: 'lead-10', address: '2000 4th Ave, Seattle', case_type: 'ESCROW_FALLOUT', priority: 'YELLOW', status: 'approved', source: 'batchdata', contact_name: 'Kim Ortiz', found_at: daysAgo(5), call_due_at: hoursAgo(8), sent_lob_at: null, sent_sendgrid_at: daysAgo(4) },
  { id: 'lead-11', address: '5600 Lake City Way NE, Seattle', case_type: 'HELOC_NO_PERMIT', priority: 'GREEN', status: 'closed', source: 'sdci', contact_name: 'Jordan Blake', found_at: daysAgo(10), call_due_at: daysAgo(8), sent_lob_at: daysAgo(9), sent_sendgrid_at: daysAgo(9) },
  { id: 'lead-12', address: '4500 Sand Point Way NE, Seattle', case_type: 'PERMIT_SNIPER', priority: 'YELLOW', status: 'contacted', source: 'sdci', contact_name: 'Taylor Morgan', found_at: daysAgo(2), call_due_at: daysAgo(1), sent_lob_at: null, sent_sendgrid_at: daysAgo(1) },
  { id: 'lead-13', address: '18920 NE 65th St, Redmond', case_type: 'NEW_PURCHASE_HELOC', priority: 'RED', status: 'email_sent', source: 'mbp', contact_name: 'Riley Brooks', found_at: hoursAgo(18), call_due_at: hoursAgo(5), sent_lob_at: daysAgo(1), sent_sendgrid_at: hoursAgo(10) },
]

export const billing = {
  batchdata: { total_cost: 19.81, success_count: 283, actual_matches: 283 },
  lob: { total_cost: 41.83, success_count: 47, actual_sent: 47 },
  sendgrid: { total_cost: 0, success_count: 122, actual_sent: 122 },
  twilio: { total_cost: 3.32, success_count: 421, actual_sent: 421 },
}

export const jobs = {
  zillow: [],
  permits: [
    {
      id: 501,
      type: 'permits',
      status: 'completed',
      year: 2026,
      permits_found: 44,
      permits_verified: 44,
      owner_builders_found: 19,
      started_at: daysAgo(2),
      completed_at: daysAgo(2),
      error_message: null,
      config: { year: 2026, permit_class: 'Single Family / Duplex', min_cost: 5000, owner_builder_check: true },
      result: { permits_found: 44, owner_builder_matches: 19, duration_seconds: 172 },
      subprocesses: [
        { id: 'sp-501-1', stage_key: 'enrichment', title: 'Обогащение контактов', status: 'completed', started_at: daysAgo(2), completed_at: daysAgo(2), result: 'Обогащено 15 записей', counts: { processed: 15, total: 15 } },
        { id: 'sp-501-2', stage_key: 'lob', title: 'Почтовая рассылка', status: 'completed', started_at: daysAgo(2), completed_at: daysAgo(2), result: 'Создано 8 писем', counts: { processed: 8, total: 8 } },
      ],
    },
    {
      id: 502,
      type: 'permits',
      status: 'verifying',
      year: 2026,
      permits_found: 26,
      permits_verified: 9,
      owner_builders_found: 4,
      started_at: hoursAgo(2),
      completed_at: null,
      error_message: null,
      config: { year: 2026, permit_class: 'Single Family / Duplex', min_cost: 7500, owner_builder_check: true },
      result: { permits_found: 26, owner_builder_matches: 4, duration_seconds: 82 },
      subprocesses: [
        { id: 'sp-502-1', stage_key: 'enrichment', title: 'Обогащение контактов', status: 'running', started_at: hoursAgo(1), completed_at: null, result: 'Обработано 5 из 9', counts: { processed: 5, total: 9 } },
      ],
    },
    {
      id: 503,
      type: 'permits',
      status: 'scheduled',
      scheduled_at: daysFromNow(0),
      started_at: null,
      completed_at: null,
      error_message: null,
      config: { year: 2026, permit_class: 'Single Family / Duplex', min_cost: 10000, owner_builder_check: true },
      result: {},
      subprocesses: [],
    },
  ],
  mbp: [
    {
      id: 601,
      type: 'mbp',
      status: 'running',
      jurisdictions: JSON.stringify(['Bellevue', 'Kirkland']),
      date_from_str: '03/10/2026',
      date_to_str: '03/20/2026',
      total_permits: 18,
      analyzed_count: 7,
      owner_builders_found: 2,
      elapsed_seconds: 318,
      current_jurisdiction: 'Bellevue',
      started_at: hoursAgo(1),
      completed_at: null,
      error_message: null,
      config: { jurisdictions: ['Bellevue', 'Kirkland'], days_back: 10, browser_visible: true },
      result: { permits_found: 18, owner_builder_matches: 2, duration_seconds: 318 },
      subprocesses: [
        { id: 'sp-601-1', stage_key: 'enrichment', title: 'Обогащение контактов', status: 'pending', started_at: null, completed_at: null, result: 'Ожидание завершения парсера' },
      ],
    },
    {
      id: 602,
      type: 'mbp',
      status: 'failed',
      jurisdictions: JSON.stringify(['Seattle']),
      date_from_str: '03/08/2026',
      date_to_str: '03/20/2026',
      total_permits: 0,
      analyzed_count: 0,
      owner_builders_found: 0,
      elapsed_seconds: 45,
      current_jurisdiction: 'Seattle',
      started_at: daysAgo(1),
      completed_at: daysAgo(1),
      error_message: 'Search returned too many results. Please refine your criteria.',
      config: { jurisdictions: ['Seattle'], days_back: 12, browser_visible: true },
      result: { permits_found: 0, owner_builder_matches: 0, duration_seconds: 45 },
      subprocesses: [
        { id: 'sp-602-1', stage_key: 'enrichment', title: 'Обогащение контактов', status: 'skipped', started_at: null, completed_at: null, result: 'Пропущено: парсер завершился с ошибкой' },
      ],
    },
    {
      id: 603,
      type: 'mbp',
      status: 'scheduled',
      scheduled_at: daysFromNow(3),
      started_at: null,
      completed_at: null,
      error_message: null,
      config: { jurisdictions: ['Redmond', 'Sammamish'], days_back: 7, browser_visible: true },
      result: {},
      subprocesses: [],
    },
  ],
}

export const dashboardAlerts = [
  { time: '09:11', level: 'warning', message: 'MBP: Bellevue поиск требует более узкий период' },
  { time: '08:57', level: 'success', message: 'SendGrid: 14 emails delivered' },
  { time: '08:31', level: 'error', message: 'Zillow job #402 завершён с ошибкой' },
]

export const mbpJurisdictions = [
  'Bellevue',
  'Redmond',
  'Kirkland',
  'Issaquah',
  'Mercer Island',
  'Sammamish',
  'Renton',
  'Bothell',
]

export const simulationStatus = {
  sim_id: 'sim-001',
  status: 'completed',
  created_at: hoursAgo(1),
}

export const scheduler = [
  { id: 'sched-1', type: 'sendgrid_campaign', run_at: daysFromNow(1), status: 'scheduled' },
  { id: 'sched-2', type: 'batchdata_skip_trace', run_at: daysFromNow(2), status: 'scheduled' },
  { id: 'sched-3', type: 'permit_parse', run_at: daysFromNow(3), status: 'scheduled' },
]
