<template>
  <div class="space-y-6 relative">
    <!-- Loading overlay при старте парсинга -->
    <div 
      v-if="startingParse"
      class="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center"
    >
      <div class="bg-white rounded-xl shadow-xl p-8 flex flex-col items-center gap-4">
        <svg class="w-12 h-12 text-purple-600 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-gray-700 font-medium">Starting MyBuildingPermit parse...</p>
        <p class="text-sm text-gray-500">Loading browser and searching permits</p>
      </div>
    </div>

    <!-- Config Section -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Parse MyBuildingPermit.com</h2>
      
      <!-- Instructions -->
      <div class="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
        <div class="flex gap-3">
          <svg class="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div class="text-sm text-gray-700">
            <p class="font-medium mb-1">About MyBuildingPermit Parser:</p>
            <ul class="list-disc list-inside space-y-1 text-gray-600">
              <li>Searches permits from permitsearch.mybuildingpermit.com</li>
              <li>Covers 13 Washington jurisdictions (King County area)</li>
              <li>Automatically identifies Owner-Builder permits (no contractor)</li>
              <li>Uses Playwright browser automation for reliable scraping</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Configuration Form -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="block text-sm font-medium text-gray-700">Jurisdictions</label>
            <div class="flex gap-2">
              <button
                type="button"
                @click="selectAllJurisdictions"
                class="text-xs text-purple-600 hover:text-purple-800 font-medium"
              >
                Select All
              </button>
              <button
                type="button"
                @click="clearAllJurisdictions"
                class="text-xs text-gray-600 hover:text-gray-800 font-medium"
              >
                Clear All
              </button>
            </div>
          </div>
          <div class="border border-gray-200 rounded-md max-h-40 overflow-y-auto p-2">
            <div v-for="(j, idx) in availableJurisdictions" :key="j" class="flex items-center mb-1">
              <input 
                type="checkbox" 
                :id="'jurisdiction-' + idx"
                :checked="selectedJurisdictions.includes(j)"
                @change="toggleJurisdiction(j, $event.target.checked)"
                class="rounded text-purple-600 focus:ring-purple-500"
              />
              <label :for="'jurisdiction-' + idx" class="ml-2 text-sm text-gray-700 cursor-pointer">{{ j }}</label>
            </div>
          </div>
          <p class="text-xs text-gray-500 mt-1">Selected: {{ selectedJurisdictions.length }} cities</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Days Back (start)</label>
          <input 
            v-model.number="config.days_back"
            type="number"
            min="1"
            max="30"
            class="w-full px-3 py-2 border border-gray-200 rounded-md focus:ring-1 focus:ring-purple-600 focus:border-purple-600"
          />
          <p class="text-xs text-gray-500 mt-1">Starts at {{ config.days_back }} days, auto-reduces if too many results</p>
        </div>
      </div>

      <div class="flex items-center justify-between">
        <div class="flex items-center gap-6">
          <div class="text-sm text-gray-500">
            <span>This will search permits and identify Owner-Builders (no contractor listed).</span>
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
          :disabled="currentJobId !== null || selectedJurisdictions.length === 0"
          class="px-6 py-2.5 bg-purple-600 text-white rounded-md font-medium hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <svg v-if="currentJobId" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          {{ currentJobId ? 'Parsing...' : 'Start Parse' }}
        </button>
      </div>
    </div>

    <!-- Ошибка парсинга — сразу видно -->
    <div 
      v-if="currentStatus && currentStatus.status === 'failed' && currentStatus.error_message" 
      class="bg-red-50 border-2 border-red-300 rounded-xl p-4 flex items-start gap-3"
    >
      <svg class="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-red-800">Парсинг завершился с ошибкой</p>
        <p class="text-sm text-red-700 mt-1 font-mono break-all">{{ currentStatus.error_message }}</p>
        <p class="text-xs text-red-600 mt-2">Job #{{ currentStatus.id }} — можно остановить или удалить задачу в истории ниже.</p>
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
            Job #{{ currentStatus.id }}
          </span>
          <span v-if="currentStatus.elapsed_seconds" class="text-sm text-gray-500">
            {{ formatElapsed(currentStatus.elapsed_seconds) }}
          </span>
        </div>

        <!-- Progress при парсинге -->
        <div v-if="isParsingActive(currentStatus.status)" class="space-y-3">
          <div class="flex justify-between items-center text-sm">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-purple-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              <span class="text-gray-700 font-medium truncate max-w-md" :title="currentStatus.current_jurisdiction">
                {{ currentStatus.current_jurisdiction || 'Initializing...' }}
              </span>
            </div>
            <span class="text-gray-900 font-medium whitespace-nowrap">
              {{ currentStatus.analyzed_count ?? 0 }}{{ currentStatus.total_permits > 0 ? ` / ${currentStatus.total_permits}` : '' }} permits
            </span>
          </div>
          <div class="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
            <div 
              class="h-full bg-purple-600 transition-all duration-300 flex items-center justify-end pr-2"
              :style="{ width: getProgressPercent() + '%' }"
            >
              <span v-if="getProgressPercent() > 10" class="text-xs text-white font-medium">
                {{ getProgressPercent().toFixed(0) }}%
              </span>
            </div>
          </div>
          <div class="flex justify-between text-xs text-gray-500">
            <span v-if="currentStatus.elapsed_seconds">
              Elapsed: {{ formatElapsed(currentStatus.elapsed_seconds) }}
            </span>
            <span v-if="currentStatus.total_permits > 0">
              {{ currentStatus.analyzed_count ?? 0 }} / {{ currentStatus.total_permits }} permits
            </span>
          </div>
        </div>

        <!-- Dates used -->
        <div v-if="currentStatus.date_from_str && currentStatus.date_to_str" class="text-sm text-gray-600">
          Period: {{ currentStatus.date_from_str }} — {{ currentStatus.date_to_str }}
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-gray-50 rounded-lg p-3">
            <p class="text-sm text-gray-500">Permits Found</p>
            <p class="text-xl font-bold text-gray-900">{{ currentStatus.total_permits }}</p>
          </div>
          <div class="bg-purple-50 rounded-lg p-3">
            <p class="text-sm text-purple-600">Owner-Builders</p>
            <p class="text-xl font-bold text-purple-700">{{ currentStatus.owner_builders_found }}</p>
          </div>
        </div>

        <div v-if="currentStatus.error_message && currentStatus.status !== 'failed'" class="bg-red-50 border border-red-200 rounded-lg p-3">
          <p class="text-sm text-red-800 font-medium">Error:</p>
          <p class="text-sm text-red-700 mt-1">{{ currentStatus.error_message }}</p>
        </div>
      </div>
    </div>

    <!-- History Section -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">Parse History</h2>
        <button 
          @click="loadJobs"
          class="text-sm text-purple-600 hover:text-purple-800"
        >
          Refresh
        </button>
      </div>

      <div v-if="loadingJobs" class="py-4">
        <div class="animate-pulse space-y-3">
          <div v-for="i in 3" :key="i" class="flex gap-4">
            <div class="h-8 bg-gray-200 rounded w-12"></div>
            <div class="h-8 bg-gray-200 rounded w-20"></div>
            <div class="h-8 bg-gray-200 rounded w-32"></div>
            <div class="h-8 bg-gray-200 rounded w-16"></div>
          </div>
        </div>
      </div>
      <div v-else-if="jobs.length === 0" class="py-8 text-center text-gray-500">
        No parse jobs yet. Start your first parse above.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Job ID</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Jurisdictions</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Permits</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owners</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="job in jobs" :key="job.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm font-medium text-gray-900">#{{ job.id }}</td>
              <td class="px-4 py-3">
                <div class="flex flex-col gap-1">
                  <span 
                    class="px-2 py-1 text-xs font-medium rounded-full flex items-center gap-1 w-fit"
                    :class="getStatusClass(job.status)"
                  >
                    <svg v-if="job.status === 'running'" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                    {{ job.status }}
                    <span v-if="job.status === 'running' && job.current_jurisdiction" class="text-xs opacity-75">
                      ({{ job.current_jurisdiction }})
                    </span>
                  </span>
                  <span v-if="job.status === 'failed' && job.error_message" class="text-xs text-red-600 max-w-xs truncate" :title="job.error_message">
                    {{ job.error_message }}
                  </span>
                </div>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                {{ parseJurisdictions(job.jurisdictions) }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ job.date_from_str && job.date_to_str ? `${job.date_from_str} — ${job.date_to_str}` : '—' }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ job.total_permits }}</td>
              <td class="px-4 py-3 text-sm font-medium text-purple-700">{{ job.owner_builders_found }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ job.elapsed_seconds ? formatElapsed(job.elapsed_seconds) : '—' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ formatDate(job.started_at) }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2 flex-wrap">
                  <!-- Cancel button -->
                  <button
                    v-if="job.status === 'running' || job.status === 'pending'"
                    @click="cancelJob(job.id)"
                    class="px-2 py-1 bg-amber-100 text-amber-700 rounded text-xs font-medium hover:bg-amber-200 transition-colors"
                    :disabled="cancellingJob === job.id"
                  >
                    {{ cancellingJob === job.id ? 'Stopping...' : 'Stop' }}
                  </button>
                  
                  <!-- Delete button -->
                  <button
                    @click="deleteJob(job.id)"
                    class="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium hover:bg-red-200 transition-colors"
                    :disabled="deletingJob === job.id"
                  >
                    {{ deletingJob === job.id ? 'Deleting...' : 'Delete' }}
                  </button>
                </div>
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
        <div class="flex items-center gap-3">
          <a
            :href="getMBPExportUrl(null, 'csv', true)"
            class="px-3 py-1.5 bg-purple-600 text-white rounded-md text-sm font-medium hover:bg-purple-700 transition-colors flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            Export CSV
          </a>
          <router-link to="/data" class="text-sm text-purple-600 hover:text-purple-800">
            View All Data
          </router-link>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Permit #</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Jurisdiction</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Address</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="permit in permits.slice(0, 10)" :key="permit.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm font-medium text-gray-900">
                <a :href="permit.permit_url" target="_blank" class="text-purple-600 hover:underline">
                  {{ permit.permit_number }}
                </a>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ permit.jurisdiction }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ permit.address }}</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ permit.permit_type }}</td>
              <td class="px-4 py-3">
                <span 
                  class="px-2 py-1 text-xs font-medium rounded-full"
                  :class="permit.is_owner_builder ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'"
                >
                  {{ permit.is_owner_builder ? 'Owner-Builder' : permit.permit_status }}
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
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { 
  getMBPJurisdictions, startMBPParse, getMBPStatus, getMBPJobs, 
  getMBPOwnerBuilders, getMBPExportUrl,
  cancelMBPJob, deleteMBPJob
} from '../api'

const availableJurisdictions = ref([])
const selectedJurisdictions = ref([])

// Set для быстрой проверки выбранных юрисдикций
const selectedSet = computed(() => new Set(selectedJurisdictions.value))

const config = reactive({
  days_back: 7,
  headless: false
})

const currentJobId = ref(null)
const currentStatus = ref(null)
const jobs = ref([])
const permits = ref([])
const loadingJobs = ref(false)
const startingParse = ref(false)
const cancellingJob = ref(null)
const deletingJob = ref(null)
let statusInterval = null

async function loadJurisdictions() {
  try {
    const data = await getMBPJurisdictions()
    availableJurisdictions.value = data.jurisdictions || []
    if (selectedJurisdictions.value.length === 0 && availableJurisdictions.value.length) {
      selectedJurisdictions.value = availableJurisdictions.value.slice(0, 4)
    }
  } catch (e) {
    console.error('Error loading jurisdictions:', e)
  }
}

function toggleJurisdiction(name, checked) {
  const current = [...selectedJurisdictions.value]
  const index = current.indexOf(name)
  
  if (checked) {
    // Добавляем, если еще нет
    if (index === -1) {
      selectedJurisdictions.value = [...current, name]
    }
  } else {
    // Удаляем, если есть
    if (index !== -1) {
      selectedJurisdictions.value = current.filter((x) => x !== name)
    }
  }
}

function selectAllJurisdictions() {
  selectedJurisdictions.value = [...availableJurisdictions.value]
}

function clearAllJurisdictions() {
  selectedJurisdictions.value = []
}

async function startParsing() {
  if (currentJobId.value || selectedJurisdictions.value.length === 0) return
  
  startingParse.value = true
  try {
    const payload = {
      jurisdictions: selectedJurisdictions.value,
      days_back: config.days_back,
      limit_per_city: null,
      headless: !config.browser_visible  // инвертируем: browser_visible=true → headless=false
    }
    const result = await startMBPParse(payload)
    currentJobId.value = result.job_id
    startingParse.value = false
    await pollStatus()
    await loadJobs()
  } catch (error) {
    startingParse.value = false
    console.error('[MBP Parse] Error starting parse:', error)
    alert('Error starting parse: ' + error.message)
  }
}

async function pollStatus() {
  if (!currentJobId.value) return
  
  try {
    const status = await getMBPStatus(currentJobId.value)
    currentStatus.value = status
    
    const finished = ['completed', 'failed', 'cancelled'].includes(status.status)
    if (finished) {
      if (statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
      currentJobId.value = null
      await loadAll()
      if (status.status === 'failed' && status.error_message) {
        setTimeout(() => alert(`Парсинг завершился с ошибкой:\n\n${status.error_message}`), 100)
      }
    }
  } catch (error) {
    if (error.message && error.message.includes('404')) {
      if (statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
      currentJobId.value = null
      currentStatus.value = null
      await loadJobs()
    }
    console.error('Error getting status:', error)
  }
}

async function loadJobs() {
  loadingJobs.value = true
  try {
    jobs.value = await getMBPJobs()
  } catch (error) {
    console.error('Error loading jobs:', error)
  } finally {
    loadingJobs.value = false
  }
}

async function loadPermits() {
  try {
    const result = await getMBPOwnerBuilders({ limit: 10 })
    permits.value = result.permits || []
  } catch (error) {
    console.error('Error loading permits:', error)
  }
}

async function loadAll() {
  await Promise.all([loadJurisdictions(), loadJobs(), loadPermits()])
}

function parseJurisdictions(jsonStr) {
  if (!jsonStr) return '—'
  try {
    const arr = JSON.parse(jsonStr)
    return Array.isArray(arr) ? arr.join(', ') : jsonStr
  } catch {
    return jsonStr
  }
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
    cancelled: 'bg-amber-100 text-amber-700',
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function isParsingActive(status) {
  return ['running', 'pending'].includes(status)
}

function isJobCancellable(status) {
  return ['running', 'pending'].includes(status)
}

function formatElapsed(seconds) {
  if (!seconds && seconds !== 0) return '—'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

function getProgressPercent() {
  if (!currentStatus.value) return 0
  const analyzed = currentStatus.value.analyzed_count ?? 0
  const total = currentStatus.value.total_permits ?? 0
  if (total === 0) {
    // Если нет total, показываем индикатор загрузки (пульсирующий)
    return 50
  }
  return Math.min(100, (analyzed / total) * 100)
}

async function cancelJob(jobId) {
  if (!confirm(`Остановить задачу #${jobId}?`)) return
  
  cancellingJob.value = jobId
  try {
    await cancelMBPJob(jobId)
    await loadJobs()
    if (currentJobId.value === jobId) {
      currentJobId.value = null
      currentStatus.value = null
      if (statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
    }
  } catch (error) {
    console.error('Error cancelling job:', error)
    alert('Ошибка при остановке задачи: ' + error.message)
  } finally {
    cancellingJob.value = null
  }
}

async function deleteJob(jobId) {
  if (!confirm(`Удалить задачу #${jobId} и все связанные данные? Это действие нельзя отменить.`)) return
  
  deletingJob.value = jobId
  try {
    await deleteMBPJob(jobId)
    await loadJobs()
    if (currentJobId.value === jobId) {
      currentJobId.value = null
      currentStatus.value = null
      if (statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
    }
    await loadPermits()
  } catch (error) {
    console.error('Error deleting job:', error)
    alert('Ошибка при удалении задачи: ' + error.message)
  } finally {
    deletingJob.value = null
  }
}

onMounted(async () => {
  await loadAll()
  // Восстанавливаем отслеживание активного job
  const activeJob = jobs.value.find(j => ['running', 'pending'].includes(j.status))
  if (activeJob) {
    currentJobId.value = activeJob.id
    await pollStatus()
  }
  statusInterval = setInterval(() => {
    if (currentJobId.value) pollStatus()
  }, 3000)
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})
</script>
