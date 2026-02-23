<template>
  <div class="space-y-6 relative">
    <!-- Loading overlay при старте парсинга -->
    <div 
      v-if="startingParse"
      class="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center"
    >
      <div class="bg-white rounded-xl shadow-xl p-8 flex flex-col items-center gap-4">
        <svg class="w-12 h-12 text-gray-900 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-gray-700 font-medium">Starting permit parse...</p>
        <p class="text-sm text-gray-500">Fetching permits from Seattle API</p>
      </div>
    </div>
    <!-- Config Section -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Parse Seattle Building Permits</h2>
      
      <!-- Instructions -->
      <div class="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
        <div class="flex gap-3">
          <svg class="w-5 h-5 text-gray-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div class="text-sm text-gray-700">
            <p class="font-medium mb-1">About Seattle Permit Parsing:</p>
            <ul class="list-disc list-inside space-y-1 text-gray-600">
              <li>Fetches building permits from Seattle Open Data Portal</li>
              <li>Filters for Single Family/Duplex permits with no contractor listed</li>
              <li>Verifies Owner-Builder status through Accela Portal (optional)</li>
              <li>Identifies potential leads for building services</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Configuration Form -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Year</label>
          <select 
            v-model="config.year"
            class="w-full px-3 py-2 border border-gray-200 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
          >
            <option :value="2026">2026</option>
            <option :value="2025">2025</option>
            <option :value="2024">2024</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Month (optional)</label>
          <select 
            v-model="config.month"
            class="w-full px-3 py-2 border border-gray-200 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
          >
            <option :value="null">All</option>
            <option :value="1">January</option>
            <option :value="2">February</option>
            <option :value="3">March</option>
            <option :value="4">April</option>
            <option :value="5">May</option>
            <option :value="6">June</option>
            <option :value="7">July</option>
            <option :value="8">August</option>
            <option :value="9">September</option>
            <option :value="10">October</option>
            <option :value="11">November</option>
            <option :value="12">December</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Permit Class</label>
          <select 
            v-model="config.permit_class"
            class="w-full px-3 py-2 border border-gray-200 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
          >
            <option value="Single Family / Duplex">Single Family / Duplex</option>
            <option value="Commercial">Commercial</option>
            <option value="Multifamily">Multifamily</option>
            <option value="">All Classes</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Minimum Cost ($)</label>
          <input 
            v-model.number="config.min_cost"
            type="number"
            min="0"
            step="1000"
            class="w-full px-3 py-2 border border-gray-200 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Verify Owner-Builder</label>
          <div class="flex items-center h-10">
            <label class="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                v-model="config.verify_owner_builder"
                class="sr-only peer"
              />
              <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-gray-400 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gray-900"></div>
              <span class="ml-3 text-sm text-gray-600">
                {{ config.verify_owner_builder ? 'Enabled' : 'Disabled' }}
              </span>
            </label>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between">
        <div class="flex items-center gap-6">
          <div class="text-sm text-gray-500">
            <span>This will fetch permits with contractor=NULL (potential owner-builders).</span>
            <span class="block mt-1 text-gray-400">Year, month, permit class and min cost are applied when you start a new parse.</span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer flex-shrink-0">
            <input 
              type="checkbox" 
              v-model="config.browser_visible"
              class="sr-only peer"
            />
            <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-gray-400 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gray-900"></div>
            <span class="ml-2 text-sm text-gray-600 whitespace-nowrap">
              Browser visible
            </span>
          </label>
        </div>
        
        <button
          @click="startParsing"
          :disabled="currentJobId !== null"
          class="px-6 py-2.5 bg-gray-900 text-white rounded-md font-medium hover:bg-black disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <svg v-if="currentJobId" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ currentJobId ? 'Parsing...' : 'Start Permit Parse' }}
        </button>
      </div>
    </div>

    <!-- Status Section -->
    <div v-if="currentStatus" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Current Parse Status</h2>
      
      <div class="space-y-4">
        <div class="flex items-center gap-4 flex-wrap">
          <span 
            class="px-3 py-1 text-sm font-medium rounded-full"
            :class="getStatusClass(currentStatus.status)"
          >
            {{ currentStatus.status }}
          </span>
          <span class="text-sm text-gray-500">
            Job #{{ currentStatus.id }} | Year: {{ currentStatus.year }}
          </span>
          <span v-if="getDuration(currentStatus)" class="text-sm text-gray-900 font-medium">
            ⏱ {{ getDuration(currentStatus) }}
          </span>
        </div>

        <!-- Progress bar при парсинге -->
        <div v-if="isParsingActive(currentStatus.status)" class="space-y-2">
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">{{ getProgressLabel(currentStatus) }}</span>
            <span v-if="currentStatus.permits_found > 0" class="text-gray-900 font-medium">
              {{ currentStatus.permits_verified }} / {{ currentStatus.permits_found }} verified
            </span>
          </div>
          <div class="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              class="h-full bg-purple-600 transition-all duration-500"
              :style="{ width: getProgressWidth(currentStatus) }"
            ></div>
          </div>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-3 gap-4">
          <div class="bg-gray-50 rounded-lg p-3">
            <p class="text-sm text-gray-500">Permits Found</p>
            <p class="text-xl font-bold text-gray-900">{{ currentStatus.permits_found ?? 0 }}</p>
          </div>
          <div class="bg-gray-50 rounded-lg p-3">
            <p class="text-sm text-gray-500">Verified</p>
            <p class="text-xl font-bold text-gray-900">{{ currentStatus.permits_verified ?? 0 }}</p>
          </div>
          <div class="bg-gray-100 rounded-lg p-3">
            <p class="text-sm text-gray-600">Owner-Builders</p>
            <p class="text-xl font-bold text-gray-900">{{ currentStatus.owner_builders_found ?? 0 }}</p>
          </div>
        </div>

        <div v-if="currentStatus.error_message" class="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p class="text-sm text-amber-800 font-medium">Note:</p>
          <p class="text-sm text-amber-700 mt-1">{{ currentStatus.error_message }}</p>
        </div>
      </div>
    </div>

    <!-- Stats Overview -->
    <div v-if="stats.total > 0" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Total Permits</p>
        <p class="text-2xl font-bold text-gray-900">{{ stats.total }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Owner-Builders</p>
        <p class="text-2xl font-bold text-gray-900">{{ stats.owner_builders }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Avg Project Cost</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.avg_cost) }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Total Value</p>
        <p class="text-2xl font-bold text-green-600">{{ formatPrice(stats.total_cost) }}</p>
      </div>
    </div>

    <!-- History Section -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">Parse History</h2>
        <button 
          @click="loadJobs"
          class="text-sm text-gray-900 hover:text-purple-700"
        >
          Refresh
        </button>
      </div>

      <div v-if="loadingJobs" class="overflow-x-auto">
        <div class="animate-pulse space-y-3 py-4">
          <div v-for="i in 5" :key="i" class="flex gap-4">
            <div class="h-8 bg-gray-200 rounded w-12"></div>
            <div class="h-8 bg-gray-200 rounded w-20"></div>
            <div class="h-8 bg-gray-200 rounded w-12"></div>
            <div class="h-8 bg-gray-200 rounded w-12"></div>
            <div class="h-8 bg-gray-200 rounded w-12"></div>
            <div class="h-8 bg-gray-200 rounded w-16"></div>
            <div class="h-8 bg-gray-200 rounded w-24"></div>
          </div>
        </div>
      </div>
      <div v-else-if="jobs.length === 0" class="py-8 text-center text-gray-500">
        No permit parse jobs yet. Start your first parse above.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Job ID</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Year</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Permits</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owners</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Error / Note</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="job in jobs" :key="job.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm font-medium text-gray-900">#{{ job.id }}</td>
              <td class="px-4 py-3">
                <span 
                  class="px-2 py-1 text-xs font-medium rounded-full"
                  :class="getStatusClass(job.status)"
                >
                  {{ job.status }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ job.year }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">
                <template v-if="job.status === 'verifying' && job.permits_found > 0">
                  {{ (job.permits_verified ?? 0) }} / {{ job.permits_found }}
                </template>
                <template v-else>{{ job.permits_found }}</template>
              </td>
              <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ job.owner_builders_found }}</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ getJobDuration(job) }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ formatDate(job.started_at) }}</td>
              <td class="px-4 py-3 text-sm max-w-xs">
                <span v-if="job.error_message" class="text-amber-700" :title="job.error_message">
                  {{ job.error_message.slice(0, 50) }}{{ job.error_message.length > 50 ? '...' : '' }}
                </span>
                <span v-else class="text-gray-400">—</span>
              </td>
              <td class="px-4 py-3 space-x-2">
                <!-- Stop button for active jobs -->
                <button
                  v-if="isParsingActive(job.status)"
                  @click="cancelJob(job.id)"
                  :disabled="cancellingJob === job.id"
                  class="text-amber-600 hover:text-amber-800 text-sm font-medium disabled:opacity-50"
                >
                  {{ cancellingJob === job.id ? 'Stopping...' : '⏹ Stop' }}
                </button>
                <!-- Export links for completed jobs -->
                <template v-if="isJobComplete(job)">
                  <a
                    v-if="job.permits_found > 0"
                    :href="getExportUrl(job.id, false)"
                    class="text-gray-900 hover:text-black text-sm"
                  >
                    All CSV
                  </a>
                  <a
                    v-if="job.permits_found > 0 && job.owner_builders_found > 0"
                    :href="getExportUrl(job.id, true)"
                    class="text-gray-900 hover:text-purple-700 text-sm font-medium"
                  >
                    Owners CSV
                  </a>
                  <span v-else-if="job.permits_found > 0 && job.owner_builders_found === 0" class="text-gray-400 text-xs">
                    (0 owners)
                  </span>
                </template>
                <span v-else-if="!isParsingActive(job.status) && job.permits_found > 0" class="text-gray-600 text-sm font-medium">
                  {{ job.status === 'verifying' ? `${job.permits_verified ?? 0} / ${job.permits_found} verified` : 'Wait for verification...' }}
                </span>
                <!-- Delete button -->
                <button
                  @click="deleteJob(job.id)"
                  :disabled="deletingJob === job.id"
                  class="text-red-500 hover:text-red-700 text-sm disabled:opacity-50 ml-2"
                  :title="'Delete job #' + job.id"
                >
                  {{ deletingJob === job.id ? '...' : '🗑' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Recent Permits Table -->
    <div v-if="permits.length > 0" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">Recent Owner-Builders</h2>
        <router-link to="/data" class="text-sm text-gray-900 hover:text-black">
          View All Data
        </router-link>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Permit #</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Address</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cost</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Applied</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="permit in permits.slice(0, 10)" :key="permit.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm font-medium text-gray-900">
                <a :href="permit.portal_link" target="_blank" class="text-gray-900 hover:underline">
                  {{ permit.permit_num }}
                </a>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ permit.address }}</td>
              <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ formatPrice(permit.est_project_cost) }}</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ permit.applied_date }}</td>
              <td class="px-4 py-3">
                <span 
                  class="px-2 py-1 text-xs font-medium rounded-full"
                  :class="permit.is_owner_builder ? 'bg-gray-900 text-white' : (permit.verification_status === 'error' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600')"
                  :title="permit.verification_status === 'error' ? (permit.work_performer_text || 'Verification did not run') : ''"
                >
                  {{ permit.is_owner_builder ? 'Owner-Builder' : (permit.verification_status === 'error' ? 'Error' : permit.verification_status) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { 
  startPermitParse, getPermitStatus, getPermitJobs, getPermitStats,
  getOwnerBuilders, getPermitExportUrl, cancelPermitJob, deletePermitJob 
} from '../api'

const config = reactive({
  year: 2026,
  month: null,
  permit_class: 'Single Family / Duplex',
  min_cost: 5000,
  verify_owner_builder: true,
  browser_visible: true  // true = видимый браузер при верификации
})

const currentJobId = ref(null)
const currentStatus = ref(null)
const jobs = ref([])
const permits = ref([])
const stats = ref({})
const loadingJobs = ref(false)
const startingParse = ref(false)
const cancellingJob = ref(null)
const deletingJob = ref(null)
let statusInterval = null

async function startParsing() {
  if (currentJobId.value) return
  
  startingParse.value = true
  try {
    const payload = {
      ...config,
      headless: !config.browser_visible
    }
    delete payload.browser_visible
    const result = await startPermitParse(payload)
    currentJobId.value = result.job_id
    startingParse.value = false
    await pollStatus()
    await loadJobs()
  } catch (error) {
    startingParse.value = false
    console.error('[PermitParse] Error starting parse:', error)
    alert('Error starting parse: ' + error.message)
  }
}

async function pollStatus() {
  if (!currentJobId.value) return
  
  try {
    const status = await getPermitStatus(currentJobId.value)
    currentStatus.value = status
    
    // Обновляем job в таблице для отображения прогресса
    const idx = jobs.value.findIndex(j => j.id === currentJobId.value)
    if (idx >= 0) {
      jobs.value[idx] = {
        ...jobs.value[idx],
        status: status.status,
        permits_found: status.permits_found ?? jobs.value[idx].permits_found,
        permits_verified: status.permits_verified ?? jobs.value[idx].permits_verified,
        owner_builders_found: status.owner_builders_found ?? jobs.value[idx].owner_builders_found,
        error_message: status.error_message,
        completed_at: status.completed_at
      }
    }
    if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
      if (statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
      currentJobId.value = null
      await loadAll()
    }
  } catch (error) {
    console.error('Error getting status:', error)
  }
}

async function loadJobs() {
  loadingJobs.value = true
  try {
    jobs.value = await getPermitJobs()
  } catch (error) {
    console.error('Error loading jobs:', error)
  } finally {
    loadingJobs.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await getPermitStats()
  } catch (error) {
    console.error('Error loading stats:', error)
  }
}

async function loadPermits() {
  try {
    const result = await getOwnerBuilders({ limit: 10 })
    permits.value = result.permits || []
  } catch (error) {
    console.error('Error loading permits:', error)
  }
}

async function loadAll() {
  await Promise.all([loadJobs(), loadStats(), loadPermits()])
}

function getExportUrl(jobId, onlyOwners = false) {
  return getPermitExportUrl(jobId, 'csv', onlyOwners)
}

function formatPrice(value) {
  if (!value) return '$0'
  return new Intl.NumberFormat('en-US', { 
    style: 'currency', 
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

function getStatusClass(status) {
  const classes = {
    completed: 'bg-green-100 text-green-700',
    running: 'bg-gray-900 text-white',
    pending: 'bg-gray-100 text-gray-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-amber-100 text-amber-700',
    fetching: 'bg-gray-100 text-gray-700',
    processing: 'bg-gray-100 text-gray-700',
    verifying: 'bg-gray-100 text-gray-700',
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function isParsingActive(status) {
  return ['running', 'fetching', 'processing', 'verifying', 'pending'].includes(status)
}

function getProgressLabel(status) {
  if (status.status === 'fetching') return 'Fetching permits from API...'
  if (status.status === 'processing') return 'Processing permits...'
  if (status.status === 'verifying') return 'Verifying owner-builder status...'
  return 'Parsing...'
}

function getProgressWidth(status) {
  if (status.permits_found > 0 && status.status === 'verifying') {
    const pct = Math.min(100, (status.permits_verified / status.permits_found) * 100)
    return `${pct}%`
  }
  return '30%'
}

function isJobComplete(job) {
  return job && ['completed', 'failed', 'cancelled'].includes(job.status)
}

async function cancelJob(jobId) {
  cancellingJob.value = jobId
  try {
    await cancelPermitJob(jobId)
    await loadJobs()
    if (currentJobId.value === jobId) {
      currentJobId.value = null
      if (statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
    }
  } catch (error) {
    console.error('Error cancelling job:', error)
    alert('Error cancelling job: ' + error.message)
  } finally {
    cancellingJob.value = null
  }
}

async function deleteJob(jobId) {
  if (!confirm(`Delete job #${jobId} and all associated permits?`)) return
  deletingJob.value = jobId
  try {
    await deletePermitJob(jobId)
    await loadAll()
  } catch (error) {
    console.error('Error deleting job:', error)
    alert('Error deleting job: ' + error.message)
  } finally {
    deletingJob.value = null
  }
}

function getJobDuration(job) {
  if (!job?.completed_at || !job?.started_at) return '—'
  return formatDuration(job.started_at, job.completed_at)
}

function getDuration(job) {
  if (!job?.completed_at || !job?.started_at) return null
  return formatDuration(job.started_at, job.completed_at)
}

function formatDuration(startedStr, completedStr) {
  if (!startedStr || !completedStr) return ''
  const start = new Date(startedStr)
  const end = new Date(completedStr)
  const sec = Math.round((end - start) / 1000)
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  const s = sec % 60
  return s > 0 ? `${min}m ${s}s` : `${min}m`
}

onMounted(async () => {
  await loadAll()
  // Восстанавливаем отслеживание активного job при возврате на страницу
  const activeJob = jobs.value.find(j => ['fetching', 'processing', 'verifying', 'pending'].includes(j.status))
  if (activeJob) {
    currentJobId.value = activeJob.id
    await pollStatus()
  }
  statusInterval = setInterval(() => {
    if (currentJobId.value) pollStatus()
  }, 2000)
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})
</script>
