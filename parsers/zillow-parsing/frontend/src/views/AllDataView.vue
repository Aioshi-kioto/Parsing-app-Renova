<template>
  <div>
    <!-- Статистика -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">Всего записей</div>
        <div class="text-2xl font-bold text-gray-900">{{ stats.total || 0 }}</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">Средняя цена</div>
        <div class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.avg_price) }}</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">Мин / Макс цена</div>
        <div class="text-lg font-semibold text-gray-900">{{ formatPrice(stats.min_price) }} / {{ formatPrice(stats.max_price) }}</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">Ср. площадь</div>
        <div class="text-2xl font-bold text-gray-900">{{ stats.avg_area_sqft || 0 }} sqft</div>
      </div>
    </div>

    <!-- Фильтры -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="text-sm font-medium text-gray-700 mb-3">Фильтры</div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label class="block text-xs text-gray-500 mb-1">Поиск (адрес, индекс, zpid)</label>
          <input
            v-model="filters.search"
            @input="debouncedLoad"
            type="text"
            placeholder="Поиск..."
            class="w-full px-3 py-2 border rounded text-sm"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Город</label>
          <input
            v-model="filters.city"
            @input="debouncedLoad"
            type="text"
            placeholder="Город"
            class="w-full px-3 py-2 border rounded text-sm"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Дата от</label>
          <input
            v-model="filters.date_from"
            @change="loadData"
            type="date"
            class="w-full px-3 py-2 border rounded text-sm"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Дата до</label>
          <input
            v-model="filters.date_to"
            @change="loadData"
            type="date"
            class="w-full px-3 py-2 border rounded text-sm"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Цена от ($)</label>
          <input
            v-model.number="filters.min_price"
            @input="debouncedLoad"
            type="number"
            placeholder="Мин"
            class="w-full px-3 py-2 border rounded text-sm"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Цена до ($)</label>
          <input
            v-model.number="filters.max_price"
            @input="debouncedLoad"
            type="number"
            placeholder="Макс"
            class="w-full px-3 py-2 border rounded text-sm"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Парсинг (job)</label>
          <select
            v-model="filters.job_id"
            @change="loadData"
            class="w-full px-3 py-2 border rounded text-sm"
          >
            <option value="">Все</option>
            <option v-for="j in jobs" :key="j.id" :value="j.id">#{{ j.id }} ({{ j.unique_homes || 0 }} домов)</option>
          </select>
        </div>
        <div class="flex items-end">
          <button
            @click="clearFilters"
            class="px-4 py-2 text-sm border rounded hover:bg-gray-50"
          >
            Сбросить
          </button>
        </div>
      </div>
    </div>

    <!-- Таблица -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-500">Загрузка...</div>
      <div v-else-if="homes.length === 0" class="p-8 text-center text-gray-500">Нет данных</div>
      <div v-else class="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50 sticky top-0">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ZPID</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Адрес</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Город</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Цена</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Кровати</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ванные</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Площадь</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Дата</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="h in homes" :key="h.id" class="hover:bg-gray-50">
              <td class="px-4 py-2 text-sm">{{ h.zpid }}</td>
              <td class="px-4 py-2 text-sm">{{ h.address }}</td>
              <td class="px-4 py-2 text-sm">{{ h.city }}, {{ h.state }} {{ h.zipcode }}</td>
              <td class="px-4 py-2 text-sm font-medium">{{ formatPrice(h.price) }}</td>
              <td class="px-4 py-2 text-sm">{{ h.beds ?? '—' }}</td>
              <td class="px-4 py-2 text-sm">{{ h.baths ?? '—' }}</td>
              <td class="px-4 py-2 text-sm">{{ h.area_sqft ? h.area_sqft + ' sqft' : '—' }}</td>
              <td class="px-4 py-2 text-sm text-gray-500">{{ formatDate(h.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="total > homes.length" class="px-4 py-2 text-sm text-gray-500 border-t">
        Показано {{ homes.length }} из {{ total }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getAllHomes, getHomesStats, getJobs } from '../api'

const homes = ref([])
const total = ref(0)
const stats = ref({})
const jobs = ref([])
const loading = ref(false)
let debounceTimer = null

const filters = reactive({
  search: '',
  city: '',
  date_from: '',
  date_to: '',
  min_price: null,
  max_price: null,
  job_id: ''
})

function formatPrice(v) {
  if (v == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v)
}

function formatDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString('ru-RU')
}

function buildParams() {
  const p = {}
  if (filters.search) p.search = filters.search
  if (filters.city) p.city = filters.city
  if (filters.date_from) p.date_from = filters.date_from
  if (filters.date_to) p.date_to = filters.date_to
  if (filters.min_price) p.min_price = filters.min_price
  if (filters.max_price) p.max_price = filters.max_price
  if (filters.job_id) p.job_id = Number(filters.job_id)
  p.limit = 500
  return p
}

async function loadData() {
  loading.value = true
  try {
    const params = buildParams()
    const [data, statsData] = await Promise.all([
      getAllHomes(params),
      getHomesStats({ job_id: params.job_id, date_from: params.date_from, date_to: params.date_to })
    ])
    homes.value = data.homes
    total.value = data.total
    stats.value = statsData
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function debouncedLoad() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadData, 300)
}

function clearFilters() {
  filters.search = ''
  filters.city = ''
  filters.date_from = ''
  filters.date_to = ''
  filters.min_price = null
  filters.max_price = null
  filters.job_id = ''
  loadData()
}

onMounted(async () => {
  jobs.value = await getJobs()
  await loadData()
})
</script>
