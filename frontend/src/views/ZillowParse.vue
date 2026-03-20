<template>
  <div class="space-y-6 relative">
    <!-- Loading overlay при старте парсинга -->
    <div 
      v-if="startingParse"
      class="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center"
    >
      <div class="bg-white rounded-xl shadow-xl p-8 flex flex-col items-center gap-4">
        <svg class="w-12 h-12 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-gray-700 font-medium">Запуск парсинга Zillow...</p>
        <p class="text-sm text-gray-500">Подготовка к загрузке {{ validUrls.length }} URL</p>
      </div>
    </div>
    <!-- Input Section -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Parse Zillow URLs</h2>
      
      <!-- Instructions -->
      <div class="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
        <div class="flex gap-3">
          <svg class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div class="text-sm text-blue-800">
            <p class="font-medium mb-1">How to use:</p>
            <ol class="list-decimal list-inside space-y-1 text-blue-700">
              <li>Go to <a href="https://zillow.com" target="_blank" class="underline">zillow.com</a></li>
              <li>Apply your filters (Sold, Price, Basement, Home Type, etc.)</li>
              <li>Set the map area you want to search</li>
              <li>Copy the URL from your browser</li>
              <li>Paste it below (one URL per line)</li>
            </ol>
          </div>
        </div>
      </div>

      <!-- URL Input -->
      <textarea
        v-model="urlsText"
        @input="validateUrls"
        placeholder="Paste Zillow URLs here, one per line...

Example:
https://www.zillow.com/seattle-wa/sold/?searchQueryState=..."
        class="w-full h-40 px-4 py-3 border border-gray-300 rounded-lg text-sm font-mono resize-none focus:ring-2 focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
      ></textarea>

      <div class="flex items-center justify-between mt-4">
        <div class="flex items-center gap-6">
          <div class="text-sm text-gray-500">
            <span v-if="validUrls.length > 0" class="text-green-600 font-medium">
              Найдено {{ validUrls.length }} URL
            </span>
            <span v-else>Введите URL Zillow для запуска парсинга</span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer flex-shrink-0">
            <input 
              type="checkbox" 
              v-model="headless"
              class="sr-only peer"
            />
            <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-gray-400 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gray-900"></div>
            <span class="ml-2 text-sm text-gray-600 whitespace-nowrap">
              {{ headless ? 'Без окна браузера' : 'Браузер виден' }}
            </span>
          </label>
        </div>
        
        <button
          @click="startParsing"
          :disabled="!canStart"
          class="px-6 py-2.5 bg-gray-900 text-white rounded-md font-medium hover:bg-black disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <svg v-if="currentJobId" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ currentJobId ? 'Парсинг...' : 'Запустить парсинг' }}
        </button>
      </div>
    </div>

    <!-- Status Section -->
    <div v-if="currentStatus" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Текущий статус парсинга</h2>
      
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
          <span v-if="formatDuration(currentStatus.started_at, currentStatus.completed_at)" class="text-sm text-blue-600 font-medium">
            ⏱ {{ formatDuration(currentStatus.started_at, currentStatus.completed_at) }}
          </span>
        </div>

        <!-- Progress -->
        <div>
          <div class="flex justify-between text-sm mb-1">
            <span class="text-gray-600">Прогресс</span>
            <span class="text-gray-900 font-medium">
              {{ currentStatus.current_url_index + 1 }} / {{ currentStatus.total_urls }} URLs
            </span>
          </div>
          <div class="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              class="h-full bg-blue-600 transition-all duration-300"
              :style="{ width: `${(currentStatus.current_url_index + 1) / currentStatus.total_urls * 100}%` }"
            ></div>
          </div>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-gray-50 rounded-lg p-3">
            <p class="text-sm text-gray-500">Найдено домов</p>
            <p class="text-xl font-bold text-gray-900">{{ currentStatus.homes_found }}</p>
          </div>
          <div class="bg-gray-50 rounded-lg p-3">
            <p class="text-sm text-gray-500">Уникальных</p>
            <p class="text-xl font-bold text-gray-900">{{ currentStatus.unique_homes }}</p>
          </div>
        </div>

        <div v-if="currentStatus.error_message" class="bg-red-50 border border-red-200 rounded-lg p-3">
          <p class="text-sm text-red-700">{{ currentStatus.error_message }}</p>
        </div>
      </div>
    </div>

    <!-- History Section -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">История парсинга</h2>
        <button 
          @click="loadJobs"
          class="text-sm text-gray-900 hover:text-black"
        >
          Обновить
        </button>
      </div>

      <div v-if="loadingJobs" class="overflow-x-auto">
        <div class="animate-pulse space-y-3 py-4">
          <div v-for="i in 5" :key="i" class="flex gap-4">
            <div class="h-8 bg-gray-200 rounded w-12"></div>
            <div class="h-8 bg-gray-200 rounded w-20"></div>
            <div class="h-8 bg-gray-200 rounded w-12"></div>
            <div class="h-8 bg-gray-200 rounded w-12"></div>
            <div class="h-8 bg-gray-200 rounded w-16"></div>
            <div class="h-8 bg-gray-200 rounded w-24"></div>
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
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Статус</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">URL</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Дома</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Длительность</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Дата</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Действия</th>
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
              <td class="px-4 py-3 text-sm text-gray-600">{{ job.total_urls }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ job.unique_homes }} / {{ job.homes_found }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ formatDate(job.started_at) }}</td>
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
                <a
                  v-if="job.unique_homes > 0"
                  :href="getExportUrl(job.id)"
                  class="text-gray-900 hover:text-black text-sm font-medium"
                >
                  Export CSV
                </a>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { startZillowParse, getZillowStatus, getZillowJobs, getZillowExportUrl, cancelZillowJob, deleteZillowJob } from '../api'

const urlsText = ref('')
const validUrls = ref([])
const currentJobId = ref(null)
const currentStatus = ref(null)
const jobs = ref([])
const loadingJobs = ref(false)
const startingParse = ref(false)
const cancellingJob = ref(null)
const deletingJob = ref(null)
const headless = ref(false)
let statusInterval = null

const canStart = computed(() => {
  return validUrls.value.length > 0 && !currentJobId.value
})

function validateUrls() {
  const lines = urlsText.value.split('\n')
  validUrls.value = lines
    .map(line => line.trim())
    .filter(line => line && line.includes('zillow.com'))
}

async function startParsing() {
  if (!canStart.value) return
  
  try {
    const result = await startZillowParse(validUrls.value, headless.value)
    currentJobId.value = result.job_id
    await pollStatus()
    await loadJobs()
  } catch (error) {
    alert('Error starting parse: ' + error.message)
  }
}

async function pollStatus() {
  if (!currentJobId.value) return
  
  try {
    const status = await getZillowStatus(currentJobId.value)
    currentStatus.value = status
    
    if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
      if (statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
      currentJobId.value = null
      await loadJobs()
    }
  } catch (error) {
    console.error('Error getting status:', error)
  }
}

async function loadJobs() {
  loadingJobs.value = true
  try {
    jobs.value = await getZillowJobs()
  } catch (error) {
    console.error('Error loading jobs:', error)
  } finally {
    loadingJobs.value = false
  }
}

function getExportUrl(jobId) {
  return getZillowExportUrl(jobId, 'csv')
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getStatusClass(status) {
  const classes = {
    completed: 'bg-green-100 text-green-700',
    running: 'bg-gray-100 text-gray-700',
    pending: 'bg-gray-100 text-gray-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-amber-100 text-amber-700',
    parsing: 'bg-blue-100 text-blue-700',
    waiting_captcha: 'bg-amber-100 text-amber-700',
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function isParsingActive(status) {
  return ['running', 'pending', 'parsing', 'waiting_captcha'].includes(status)
}

async function cancelJob(jobId) {
  cancellingJob.value = jobId
  try {
    await cancelZillowJob(jobId)
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
  if (!confirm(`Delete job #${jobId} and all associated homes?`)) return
  deletingJob.value = jobId
  try {
    await deleteZillowJob(jobId)
    await loadJobs()
  } catch (error) {
    console.error('Error deleting job:', error)
    alert('Error deleting job: ' + error.message)
  } finally {
    deletingJob.value = null
  }
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
  await loadJobs()
  // Восстанавливаем отслеживание активного job при возврате на страницу
  const activeJob = jobs.value.find(j => isParsingActive(j.status))
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
