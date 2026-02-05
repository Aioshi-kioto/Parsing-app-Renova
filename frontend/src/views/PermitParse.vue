<template>
  <div class="space-y-6">
    <!-- Config Section -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Parse Seattle Building Permits</h2>
      
      <!-- Instructions -->
      <div class="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
        <div class="flex gap-3">
          <svg class="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div class="text-sm text-purple-800">
            <p class="font-medium mb-1">About Seattle Permit Parsing:</p>
            <ul class="list-disc list-inside space-y-1 text-purple-700">
              <li>Fetches building permits from Seattle Open Data Portal</li>
              <li>Filters for Single Family/Duplex permits with no contractor listed</li>
              <li>Verifies Owner-Builder status through Accela Portal (optional)</li>
              <li>Identifies potential leads for building services</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Configuration Form -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Period</label>
          <select 
            v-model="config.period"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          >
            <option :value="null">Full year</option>
            <option value="last_month">Last month</option>
            <option value="last_3_months">Last 3 months</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Year</label>
          <select 
            v-model="config.year"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
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
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
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
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
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
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
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
              <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
              <span class="ml-3 text-sm text-gray-600">
                {{ config.verify_owner_builder ? 'Enabled' : 'Disabled' }}
              </span>
            </label>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between">
        <div class="text-sm text-gray-500">
          This will fetch permits with contractor=NULL (potential owner-builders)
        </div>
        
        <button
          @click="startParsing"
          :disabled="currentJobId !== null"
          class="px-6 py-2.5 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
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
        <div class="flex items-center gap-4">
          <span 
            class="px-3 py-1 text-sm font-medium rounded-full"
            :class="getStatusClass(currentStatus.status)"
          >
            {{ currentStatus.status }}
          </span>
          <span class="text-sm text-gray-500">
            Job #{{ currentStatus.id }} | Year: {{ currentStatus.year }}
          </span>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-3 gap-4">
          <div class="bg-gray-50 rounded-lg p-3">
            <p class="text-sm text-gray-500">Permits Found</p>
            <p class="text-xl font-bold text-gray-900">{{ currentStatus.permits_found }}</p>
          </div>
          <div class="bg-gray-50 rounded-lg p-3">
            <p class="text-sm text-gray-500">Verified</p>
            <p class="text-xl font-bold text-gray-900">{{ currentStatus.permits_verified }}</p>
          </div>
          <div class="bg-purple-50 rounded-lg p-3">
            <p class="text-sm text-purple-600">Owner-Builders</p>
            <p class="text-xl font-bold text-purple-700">{{ currentStatus.owner_builders_found }}</p>
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
        <p class="text-2xl font-bold text-purple-600">{{ stats.owner_builders }}</p>
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
          class="text-sm text-purple-600 hover:text-purple-700"
        >
          Refresh
        </button>
      </div>

      <div v-if="loadingJobs" class="py-8 text-center text-gray-500">
        Loading...
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
              <td class="px-4 py-3 text-sm text-gray-600">{{ job.permits_found }}</td>
              <td class="px-4 py-3 text-sm font-medium text-purple-600">{{ job.owner_builders_found }}</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ formatDate(job.started_at) }}</td>
              <td class="px-4 py-3 text-sm max-w-xs">
                <span v-if="job.error_message" class="text-amber-700" :title="job.error_message">
                  {{ job.error_message.slice(0, 50) }}{{ job.error_message.length > 50 ? '...' : '' }}
                </span>
                <span v-else class="text-gray-400">—</span>
              </td>
              <td class="px-4 py-3 space-x-2">
                <a
                  v-if="job.permits_found > 0"
                  :href="getExportUrl(job.id, false)"
                  class="text-blue-600 hover:text-blue-700 text-sm"
                >
                  All CSV
                </a>
                <a
                  v-if="job.owner_builders_found > 0"
                  :href="getExportUrl(job.id, true)"
                  class="text-purple-600 hover:text-purple-700 text-sm font-medium"
                >
                  Owners CSV
                </a>
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
        <router-link to="/data" class="text-sm text-purple-600 hover:text-purple-700">
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
                <a :href="permit.portal_link" target="_blank" class="text-blue-600 hover:underline">
                  {{ permit.permit_num }}
                </a>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ permit.address }}</td>
              <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ formatPrice(permit.est_project_cost) }}</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ permit.applied_date }}</td>
              <td class="px-4 py-3">
                <span 
                  class="px-2 py-1 text-xs font-medium rounded-full"
                  :class="permit.is_owner_builder ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'"
                >
                  {{ permit.is_owner_builder ? 'Owner-Builder' : permit.verification_status }}
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
  getOwnerBuilders, getPermitExportUrl 
} from '../api'

const config = reactive({
  year: 2026,
  permit_class: 'Single Family / Duplex',
  min_cost: 5000,
  verify_owner_builder: true
})

const currentJobId = ref(null)
const currentStatus = ref(null)
const jobs = ref([])
const permits = ref([])
const stats = ref({})
const loadingJobs = ref(false)
let statusInterval = null

async function startParsing() {
  if (currentJobId.value) return
  
  try {
    const result = await startPermitParse(config)
    currentJobId.value = result.job_id
    await pollStatus()
    await loadJobs()
  } catch (error) {
    console.error('[PermitParse] Error starting parse:', error)
    alert('Error starting parse: ' + error.message)
  }
}

async function pollStatus() {
  if (!currentJobId.value) return
  
  try {
    const status = await getPermitStatus(currentJobId.value)
    currentStatus.value = status
    
    if (status.status === 'completed' || status.status === 'failed') {
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
    running: 'bg-purple-100 text-purple-700',
    pending: 'bg-gray-100 text-gray-700',
    failed: 'bg-red-100 text-red-700',
    fetching: 'bg-blue-100 text-blue-700',
    processing: 'bg-blue-100 text-blue-700',
    verifying: 'bg-amber-100 text-amber-700',
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

onMounted(async () => {
  await loadAll()
  statusInterval = setInterval(() => {
    if (currentJobId.value) pollStatus()
  }, 3000)
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})
</script>
