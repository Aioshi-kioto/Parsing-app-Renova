<template>
  <div class="bg-white border border-gray-200 rounded-lg p-6">
    <h3 class="text-lg font-semibold mb-4">История парсингов</h3>
    
    <div v-if="loading" class="text-center py-8 text-gray-500">
      Загрузка...
    </div>
    
    <div v-else-if="jobs.length === 0" class="text-center py-8 text-gray-500">
      Нет парсингов
    </div>
    
    <div v-else class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Дата</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">URL</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Домов</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Статус</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Действия</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="job in jobs" :key="job.id">
            <td class="px-4 py-3 text-sm">{{ job.id }}</td>
            <td class="px-4 py-3 text-sm">{{ formatDate(job.started_at) }}</td>
            <td class="px-4 py-3 text-sm">{{ job.total_urls }}</td>
            <td class="px-4 py-3 text-sm">
              {{ job.unique_homes || job.homes_found || 0 }}
            </td>
            <td class="px-4 py-3 text-sm">
              <span :class="getStatusColor(job.status)" class="px-2 py-1 rounded text-xs font-medium">
                {{ getStatusText(job.status) }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm">
              <a
                v-if="job.status === 'completed'"
                :href="getExportUrl(job.id)"
                class="text-blue-600 hover:text-blue-800 mr-3"
              >
                Экспорт CSV
              </a>
              <button
                @click="$emit('view-job', job.id)"
                class="text-blue-600 hover:text-blue-800"
              >
                Просмотр
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { getExportUrl } from '../api'

const props = defineProps({
  jobs: Array,
  loading: Boolean
})

defineEmits(['view-job'])

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })
}

function getStatusText(status) {
  const map = {
    pending: 'Ожидание',
    waiting_captcha: 'Капча',
    parsing: 'Парсинг',
    completed: 'Завершено',
    failed: 'Ошибка'
  }
  return map[status] || status
}

function getStatusColor(status) {
  const map = {
    pending: 'bg-gray-100 text-gray-800',
    waiting_captcha: 'bg-yellow-100 text-yellow-800',
    parsing: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800'
  }
  return map[status] || 'bg-gray-100 text-gray-800'
}
</script>
