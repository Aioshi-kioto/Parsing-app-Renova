<template>
  <div v-if="status" class="bg-white border border-gray-200 rounded-lg p-6 mb-6">
    <h3 class="text-lg font-semibold mb-4">Статус парсинга</h3>
    
    <div class="space-y-4">
      <div>
        <div class="flex justify-between items-center mb-2">
          <span class="text-sm font-medium text-gray-700">Прогресс</span>
          <span class="text-sm text-gray-600">
            URL {{ status.current_url_index + 1 }} из {{ status.total_urls }}
          </span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2.5">
          <div
            class="bg-gray-900 h-2.5 rounded-full transition-all duration-300"
            :style="{ width: `${progressPercent}%` }"
          ></div>
        </div>
      </div>
      
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="text-sm text-gray-600">Статус</div>
          <div class="text-lg font-semibold" :class="statusColor">
            {{ statusText }}
          </div>
        </div>
        <div>
          <div class="text-sm text-gray-600">Найдено домов</div>
          <div class="text-lg font-semibold">{{ status.homes_found || 0 }}</div>
        </div>
        <div>
          <div class="text-sm text-gray-600">Уникальных</div>
          <div class="text-lg font-semibold">{{ status.unique_homes || 0 }}</div>
        </div>
        <div>
          <div class="text-sm text-gray-600">Время</div>
          <div class="text-sm">{{ formatTime(status.started_at) }}</div>
        </div>
      </div>
      
      <div v-if="status.status === 'waiting_captcha'" class="bg-yellow-50 border border-yellow-200 rounded p-3">
        <p class="text-sm text-yellow-800">
          ⚠️ Откройте браузер, который автоматически запустился, и пройдите капчу Zillow.
          После прохождения капчи парсинг продолжится автоматически.
        </p>
      </div>
      
      <div v-if="status.error_message" class="bg-red-50 border border-red-200 rounded p-3">
        <p class="text-sm text-red-800">
          ❌ Ошибка: {{ status.error_message }}
        </p>
      </div>
      
      <div v-if="status.status === 'completed'" class="bg-green-50 border border-green-200 rounded p-3">
        <p class="text-sm text-green-800">
          ✅ Парсинг завершён успешно!
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: Object
})

const progressPercent = computed(() => {
  if (!props.status || props.status.total_urls === 0) return 0
  return ((props.status.current_url_index + 1) / props.status.total_urls) * 100
})

const statusText = computed(() => {
  const statusMap = {
    pending: 'Ожидание',
    waiting_captcha: 'Ожидание капчи',
    parsing: 'Парсинг',
    completed: 'Завершено',
    failed: 'Ошибка'
  }
  return statusMap[props.status?.status] || props.status?.status || ''
})

const statusColor = computed(() => {
  const colorMap = {
    pending: 'text-gray-600',
    waiting_captcha: 'text-yellow-600',
    parsing: 'text-gray-900',
    completed: 'text-green-600',
    failed: 'text-red-600'
  }
  return colorMap[props.status?.status] || 'text-gray-600'
})

function formatTime(timeStr) {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleString('ru-RU')
}
</script>
