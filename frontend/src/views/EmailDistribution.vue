<template>
  <div class="space-y-6">
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Рассылка по почте</h2>

      <!-- Информация -->
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <div class="flex gap-3">
          <svg class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
          <div class="text-sm text-blue-800">
            <p class="font-medium mb-1">Email рассылка</p>
            <p class="text-blue-700">Выберите источник данных и составьте письмо для рассылки по собранным контактам (owner-builders, пермиты и т.д.)</p>
          </div>
        </div>
      </div>

      <!-- Источник получателей -->
      <div class="mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-2">Источник получателей</label>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            v-for="src in recipientSources"
            :key="src.id"
            @click="selectedSource = src.id"
            class="flex items-start gap-3 p-4 rounded-lg border-2 transition-colors text-left"
            :class="selectedSource === src.id 
              ? 'border-indigo-500 bg-indigo-50' 
              : 'border-gray-200 hover:border-gray-300 bg-white'"
          >
            <div class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                 :class="selectedSource === src.id ? 'bg-indigo-100' : 'bg-gray-100'">
              <component :is="src.icon" class="w-5 h-5" :class="selectedSource === src.id ? 'text-indigo-600' : 'text-gray-500'" />
            </div>
            <div>
              <p class="font-medium text-gray-900">{{ src.name }}</p>
              <p class="text-sm text-gray-500 mt-0.5">{{ src.description }}</p>
              <p class="text-xs text-gray-400 mt-1">{{ src.count }} получателей</p>
            </div>
          </button>
        </div>
      </div>

      <!-- Тема и текст письма -->
      <div class="space-y-4 mb-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Тема письма</label>
          <input
            v-model="emailSubject"
            type="text"
            placeholder="Например: Предложение по ремонту"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Текст письма</label>
          <textarea
            v-model="emailBody"
            rows="6"
            placeholder="Здравствуйте!&#10;&#10;Ваш текст здесь..."
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p class="text-xs text-gray-500 mt-1">Поддерживаются переменные: &#123;&#123;address&#125;&#125;, &#123;&#123;city&#125;&#125;, &#123;&#123;permit_number&#125;&#125;</p>
        </div>
      </div>

      <!-- Действия -->
      <div class="flex items-center justify-between pt-4 border-t border-gray-200">
        <p class="text-sm text-gray-500">
          Будет отправлено: <span class="font-medium text-gray-700">{{ recipientCount }} писем</span>
        </p>
        <button
          @click="sendEmails"
          :disabled="sending || recipientCount === 0 || !emailSubject.trim()"
          class="px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <svg v-if="sending" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          {{ sending ? 'Отправка...' : 'Отправить рассылку' }}
        </button>
      </div>
    </div>

    <!-- История рассылок (заглушка) -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 class="text-base font-semibold text-gray-900 mb-4">История рассылок</h3>
      <div class="text-center py-8 text-gray-500">
        <svg class="w-12 h-12 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
        </svg>
        <p class="text-sm">История рассылок появится здесь после настройки backend</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { getPermitStats, getMBPStats } from '../api'

const selectedSource = ref('mbp_owners')
const emailSubject = ref('')
const emailBody = ref('')
const sending = ref(false)

const permitStats = ref({ total: 0, owner_builders: 0 })
const mbpStats = ref({ total: 0, owner_builders_from_matching: 0 })

const MailIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' })
    ])
  }
}

const recipientSources = computed(() => [
  {
    id: 'mbp_owners',
    name: 'MyBuildingPermit — Owner-Builders',
    description: 'Владельцы без подрядчика',
    count: mbpStats.value.owner_builders_from_matching || 0,
    icon: MailIcon
  },
  {
    id: 'permits_owners',
    name: 'Building Permits — Owner-Builders',
    description: 'Пермиты Seattle (owner-builder)',
    count: permitStats.value.owner_builders || 0,
    icon: MailIcon
  }
])

const recipientCount = computed(() => {
  const src = recipientSources.value.find(s => s.id === selectedSource.value)
  return src?.count || 0
})

async function loadStats() {
  try {
    const [permits, mbp] = await Promise.all([
      getPermitStats().catch(() => ({ total: 0, owner_builders: 0 })),
      getMBPStats().catch(() => ({ total: 0, owner_builders_from_matching: 0 }))
    ])
    permitStats.value = permits
    mbpStats.value = mbp
  } catch (e) {
    console.error('Error loading stats:', e)
  }
}

async function sendEmails() {
  if (recipientCount.value === 0 || !emailSubject.value.trim()) return
  sending.value = true
  try {
    // TODO: backend API для рассылки
    alert('Функция рассылки будет доступна после настройки email-сервера на backend.')
  } finally {
    sending.value = false
  }
}

onMounted(loadStats)
</script>
