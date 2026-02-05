<template>
  <div>
    <ParseRules />
    
    <div class="bg-white rounded-lg shadow p-6 mb-6">
      <UrlInput v-model="urlsText" @urls-changed="handleUrlsChanged" />
      
      <button
        @click="startParsing"
        :disabled="!canStart"
        class="w-full py-3 px-6 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        {{ currentJobId ? 'Парсинг запущен...' : 'Запустить парсинг' }}
      </button>
    </div>
    
    <ParseStatus v-if="currentStatus" :status="currentStatus" />
    
    <ParseHistory :jobs="jobs" :loading="loadingJobs" @view-job="handleViewJob" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import ParseRules from '../components/ParseRules.vue'
import UrlInput from '../components/UrlInput.vue'
import ParseStatus from '../components/ParseStatus.vue'
import ParseHistory from '../components/ParseHistory.vue'
import { startParse, getStatus, getJobs } from '../api'

const urlsText = ref('')
const validUrls = ref([])
const currentJobId = ref(null)
const currentStatus = ref(null)
const jobs = ref([])
const loadingJobs = ref(false)
let statusInterval = null

const canStart = computed(() => {
  return validUrls.value.length > 0 && !currentJobId.value
})

function handleUrlsChanged(urls) {
  validUrls.value = urls
}

async function startParsing() {
  if (!canStart.value) return
  
  try {
    const result = await startParse(validUrls.value)
    currentJobId.value = result.job_id
    await pollStatus()
    await loadJobs()
  } catch (error) {
    alert('Ошибка запуска парсинга: ' + error.message)
  }
}

async function pollStatus() {
  if (!currentJobId.value) return
  
  try {
    const status = await getStatus(currentJobId.value)
    currentStatus.value = status
    
    if (status.status === 'completed' || status.status === 'failed') {
      if (statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
      currentJobId.value = null
      await loadJobs()
    }
  } catch (error) {
    console.error('Ошибка получения статуса:', error)
  }
}

async function loadJobs() {
  loadingJobs.value = true
  try {
    jobs.value = await getJobs()
  } catch (error) {
    console.error('Ошибка загрузки списка:', error)
  } finally {
    loadingJobs.value = false
  }
}

function handleViewJob(jobId) {
  console.log('View job:', jobId)
}

onMounted(async () => {
  await loadJobs()
  statusInterval = setInterval(() => {
    if (currentJobId.value) pollStatus()
  }, 2000)
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})
</script>
