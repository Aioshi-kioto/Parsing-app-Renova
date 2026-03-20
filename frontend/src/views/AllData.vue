<template>
  <div class="space-y-4 animate-fadeIn">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <div class="text-[10px] mb-1" style="color: var(--text-muted);">/данные/{{ activeDataset }}</div>
        <h1 class="text-xl font-bold tracking-wide" style="color: var(--text-primary);">ВСЕ ДАННЫЕ</h1>
      </div>
      <div class="flex gap-2">
        <a :href="exportCsvUrl" class="btn-secondary" download>CSV</a>
        <a :href="exportExcelUrl" class="btn-primary" download>XLSX</a>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-0 border-b" style="border-color: var(--border);">
      <button
        v-for="tab in datasetTabs"
        :key="tab.id"
        class="terminal-tab"
        :class="{ active: activeDataset === tab.id }"
        @click="switchDataset(tab.id)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Compact Filter Bar -->
    <div class="flex items-center gap-2 flex-wrap py-2 px-3 border" style="border-color: var(--border); background: var(--bg-surface);">
      <input
        v-model="filters.search"
        type="text"
        placeholder="поиск..."
        class="py-1 px-2 w-36 text-[10px]"
        @keyup.enter="loadData"
      />
      <span class="text-[10px]" style="color: var(--text-muted);">|</span>
      <input
        v-model="filters.city"
        type="text"
        :placeholder="activeDataset === 'mbp' ? 'юрисдикция' : 'город'"
        class="py-1 px-2 w-28 text-[10px]"
        @keyup.enter="loadData"
      />
      <span class="text-[10px]" style="color: var(--text-muted);">|</span>
      <template v-if="activeDataset !== 'leads'">
        <input
          v-model.number="filters.minPrice"
          type="number"
          placeholder="мин $"
          class="py-1 px-2 w-20 text-[10px]"
        />
        <input
          v-model.number="filters.maxPrice"
          type="number"
          placeholder="макс $"
          class="py-1 px-2 w-20 text-[10px]"
        />
        <span class="text-[10px]" style="color: var(--text-muted);">|</span>
      </template>
      <template v-if="activeDataset === 'permits' || activeDataset === 'mbp'">
        <select v-model="filters.isOwnerBuilder" class="py-1 px-2 text-[10px]">
          <option :value="null">владелец: все</option>
          <option :value="true">владелец: да</option>
          <option :value="false">владелец: нет</option>
        </select>
        <span class="text-[10px]" style="color: var(--text-muted);">|</span>
      </template>
      <template v-if="activeDataset === 'leads'">
        <select v-model="filters.caseType" class="py-1 px-2 text-[10px]">
          <option value="">кейс: все</option>
          <option v-for="ct in caseTypes" :key="ct" :value="ct">{{ ct }}</option>
        </select>
        <select v-model="filters.priority" class="py-1 px-2 text-[10px]">
          <option value="">приоритет: все</option>
          <option value="RED">Высокий</option>
          <option value="YELLOW">Средний</option>
          <option value="GREEN">Низкий</option>
        </select>
        <select v-model="filters.status" class="py-1 px-2 text-[10px]">
          <option value="">статус: все</option>
          <option v-for="s in leadStatuses" :key="s" :value="s">{{ leadStatusLabel(s) }}</option>
        </select>
        <span class="text-[10px]" style="color: var(--text-muted);">|</span>
      </template>
      <button class="btn-primary py-1 px-3" @click="loadData">Применить</button>
      <button class="btn-secondary py-1 px-3" @click="resetFilters">Сбросить</button>
    </div>

    <!-- Data Table -->
    <div class="card p-0">
      <div v-if="loading" class="p-8 text-center text-[11px]" style="color: var(--text-muted);">загрузка...</div>
      <div v-else-if="data.length === 0" class="p-8 text-center text-[11px]" style="color: var(--text-muted);">ничего не найдено</div>
      <div v-else class="overflow-x-auto">
        <!-- Zillow -->
        <table v-if="activeDataset === 'zillow'" class="w-full">
          <thead>
            <tr>
              <th v-for="col in zillowCols" :key="col.key" class="table-header cursor-pointer select-none" @click="toggleSort(col.key)">
                {{ col.label }} {{ sortIndicator(col.key) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedData" :key="row.zpid" class="hover-row">
              <td class="table-cell">{{ row.zpid }}</td>
              <td class="table-cell truncate" style="color: var(--text-primary); max-width: 200px;">{{ row.address }}</td>
              <td class="table-cell">{{ row.city }}</td>
              <td class="table-cell">{{ row.zip_code }}</td>
              <td class="table-cell">{{ formatPrice(row.price) }}</td>
              <td class="table-cell">{{ row.beds || '-' }}</td>
              <td class="table-cell">{{ row.baths || '-' }}</td>
              <td class="table-cell">{{ row.sqft || '-' }}</td>
              <td class="table-cell">{{ row.home_type || '-' }}</td>
            </tr>
          </tbody>
        </table>

        <!-- Permits -->
        <table v-if="activeDataset === 'permits'" class="w-full">
          <thead>
            <tr>
              <th v-for="col in permitCols" :key="col.key" class="table-header cursor-pointer select-none" @click="toggleSort(col.key)">
                {{ col.label }} {{ sortIndicator(col.key) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedData" :key="row.permit_number" class="hover-row">
              <td class="table-cell" style="color: var(--accent-cyan);">{{ row.permit_number }}</td>
              <td class="table-cell truncate" style="max-width: 180px;">{{ row.address }}</td>
              <td class="table-cell">{{ row.city }}</td>
              <td class="table-cell truncate" style="max-width: 160px;">{{ row.description || '-' }}</td>
              <td class="table-cell">{{ formatPrice(row.project_cost) }}</td>
              <td class="table-cell">{{ row.permit_class || '-' }}</td>
              <td class="table-cell">{{ row.status || '-' }}</td>
              <td class="table-cell">
                <span class="badge" :class="row.is_owner_builder ? 'badge-green' : 'badge-gray'">
                  {{ row.is_owner_builder ? 'Да' : 'Нет' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- MBP -->
        <table v-if="activeDataset === 'mbp'" class="w-full">
          <thead>
            <tr>
              <th v-for="col in mbpCols" :key="col.key" class="table-header cursor-pointer select-none" @click="toggleSort(col.key)">
                {{ col.label }} {{ sortIndicator(col.key) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedData" :key="row.permit_number" class="hover-row">
              <td class="table-cell" style="color: var(--accent-cyan);">{{ row.permit_number }}</td>
              <td class="table-cell">{{ row.jurisdiction }}</td>
              <td class="table-cell truncate" style="max-width: 180px;">{{ row.address }}</td>
              <td class="table-cell">{{ row.permit_type || '-' }}</td>
              <td class="table-cell">{{ row.status || '-' }}</td>
              <td class="table-cell">{{ row.applicant_name || '-' }}</td>
              <td class="table-cell">
                <span class="badge" :class="row.is_owner_builder ? 'badge-green' : 'badge-gray'">
                  {{ row.is_owner_builder ? 'Да' : 'Нет' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Leads -->
        <table v-if="activeDataset === 'leads'" class="w-full">
          <thead>
            <tr>
              <th v-for="col in leadCols" :key="col.key" class="table-header cursor-pointer select-none" @click="toggleSort(col.key)">
                {{ col.label }} {{ sortIndicator(col.key) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedData" :key="row.id" class="hover-row">
              <td class="table-cell truncate" style="max-width: 180px;">{{ row.address }}</td>
              <td class="table-cell">
                <span class="badge badge-case">{{ row.case_type }}</span>
              </td>
              <td class="table-cell">
                <span class="badge" :class="priorityBadge(row.priority)">{{ row.priority }}</span>
              </td>
              <td class="table-cell">{{ leadStatusLabel(row.status) }}</td>
              <td class="table-cell">{{ row.source || '-' }}</td>
              <td class="table-cell">{{ row.contact_name || '-' }}</td>
              <td class="table-cell">{{ formatDate(row.found_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between px-3 py-2 border-t" style="border-color: var(--border);">
        <span class="text-[10px]" style="color: var(--text-muted);">
          {{ (pagination.page - 1) * pagination.limit + 1 }}-{{ Math.min(pagination.page * pagination.limit, total) }} of {{ total }}
        </span>
        <div class="flex items-center gap-2">
          <button class="btn-secondary py-1 px-2 text-[10px]" :disabled="pagination.page === 1" @click="prevPage">Назад</button>
          <span class="text-[10px]" style="color: var(--text-secondary);">{{ pagination.page }}</span>
          <button class="btn-secondary py-1 px-2 text-[10px]" :disabled="pagination.page * pagination.limit >= total" @click="nextPage">Вперёд</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import {
  getZillowHomes, getZillowExportAllUrl,
  getPermits, getPermitExportAllUrl,
  getMBPPermits, getMBPExportUrl,
  getLeads
} from '../api'

const activeDataset = ref('zillow')
const data = ref([])
const total = ref(0)
const loading = ref(false)
const sortKey = ref('')
const sortDir = ref('asc')

const filters = reactive({
  search: '', city: '', minPrice: null, maxPrice: null,
  isOwnerBuilder: null, caseType: '', priority: '', status: ''
})
const pagination = reactive({ page: 1, limit: 50 })

const caseTypes = ['PERMIT_SNIPER', 'EMERGENCY_PLUMBING', 'HELOC_NO_PERMIT', 'NEW_PURCHASE_HELOC', 'MECHANICS_LIEN', 'ESCROW_FALLOUT', 'ELECTRICAL_REWIRE', 'STORM_ROOF_DAMAGE', 'GENERAL']
const leadStatuses = ['new', 'pending_review', 'approved', 'letter_sent', 'email_sent', 'contacted', 'no_answer', 'closed']

const datasetTabs = [
  { id: 'zillow', label: 'Zillow' },
  { id: 'permits', label: 'Пермиты' },
  { id: 'mbp', label: 'MBP' },
  { id: 'leads', label: 'Лиды' },
]

const leadStatusLabels = { new: 'Новый', pending_review: 'На проверке', approved: 'Одобрен', letter_sent: 'Письмо отправлено', email_sent: 'Email отправлен', contacted: 'Связались', no_answer: 'Не ответил', closed: 'Архив' }
function leadStatusLabel(s) { return leadStatusLabels[s] || s }

const zillowCols = [
  { key: 'zpid', label: 'zpid' }, { key: 'address', label: 'адрес' }, { key: 'city', label: 'город' },
  { key: 'zip_code', label: 'индекс' }, { key: 'price', label: 'цена' }, { key: 'beds', label: 'спален' },
  { key: 'baths', label: 'ванн' }, { key: 'sqft', label: 'кв.ф' }, { key: 'home_type', label: 'тип' },
]
const permitCols = [
  { key: 'permit_number', label: '№ пермита' }, { key: 'address', label: 'адрес' }, { key: 'city', label: 'город' },
  { key: 'description', label: 'описание' }, { key: 'project_cost', label: 'стоимость' }, { key: 'permit_class', label: 'класс' },
  { key: 'status', label: 'статус' }, { key: 'is_owner_builder', label: 'владелец' },
]
const mbpCols = [
  { key: 'permit_number', label: '№ пермита' }, { key: 'jurisdiction', label: 'юрисдикция' }, { key: 'address', label: 'адрес' },
  { key: 'permit_type', label: 'тип' }, { key: 'status', label: 'статус' }, { key: 'applicant_name', label: 'заявитель' },
  { key: 'is_owner_builder', label: 'владелец' },
]
const leadCols = [
  { key: 'address', label: 'адрес' }, { key: 'case_type', label: 'кейс' }, { key: 'priority', label: 'приоритет' },
  { key: 'status', label: 'статус' }, { key: 'source', label: 'источник' }, { key: 'contact_name', label: 'контакт' },
  { key: 'found_at', label: 'найден' },
]

const sortedData = computed(() => {
  if (!sortKey.value) return data.value
  const list = [...data.value]
  list.sort((a, b) => {
    let va = a[sortKey.value], vb = b[sortKey.value]
    if (va == null) va = ''
    if (vb == null) vb = ''
    if (typeof va === 'number' && typeof vb === 'number') return sortDir.value === 'asc' ? va - vb : vb - va
    return sortDir.value === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va))
  })
  return list
})

const exportCsvUrl = computed(() => {
  if (activeDataset.value === 'zillow') return getZillowExportAllUrl({ ...buildFilterParams(), format: 'csv' })
  if (activeDataset.value === 'mbp') return getMBPExportUrl(null, 'csv', filters.isOwnerBuilder === true)
  return getPermitExportAllUrl({ ...buildFilterParams(), format: 'csv' })
})
const exportExcelUrl = computed(() => {
  if (activeDataset.value === 'zillow') return getZillowExportAllUrl({ ...buildFilterParams(), format: 'xlsx' })
  if (activeDataset.value === 'mbp') return getMBPExportUrl(null, 'xlsx', filters.isOwnerBuilder === true)
  return getPermitExportAllUrl({ ...buildFilterParams(), format: 'xlsx' })
})

function buildFilterParams() {
  const params = {}
  if (filters.search) params.search = filters.search
  if (filters.city && activeDataset.value === 'mbp') params.jurisdiction = filters.city
  else if (filters.city) params.city = filters.city
  if (filters.minPrice) params[activeDataset.value === 'zillow' ? 'min_price' : 'min_cost'] = filters.minPrice
  if (filters.maxPrice) params[activeDataset.value === 'zillow' ? 'max_price' : 'max_cost'] = filters.maxPrice
  if ((activeDataset.value === 'permits' || activeDataset.value === 'mbp') && filters.isOwnerBuilder !== null) params.is_owner_builder = filters.isOwnerBuilder
  if (activeDataset.value === 'leads') {
    if (filters.caseType) params.case_type = filters.caseType
    if (filters.priority) params.priority = filters.priority
    if (filters.status) params.status = filters.status
  }
  return params
}

function toggleSort(key) {
  if (sortKey.value === key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  else { sortKey.value = key; sortDir.value = 'asc' }
}
function sortIndicator(key) {
  if (sortKey.value !== key) return ''
  return sortDir.value === 'asc' ? '^' : 'v'
}

async function loadData() {
  loading.value = true
  try {
    const params = { ...buildFilterParams(), skip: (pagination.page - 1) * pagination.limit, limit: pagination.limit }
    if (activeDataset.value === 'zillow') {
      const r = await getZillowHomes(params); data.value = r.homes || []; total.value = r.total || 0
    } else if (activeDataset.value === 'mbp') {
      const r = await getMBPPermits(params); data.value = r.permits || []; total.value = r.total || 0
    } else if (activeDataset.value === 'leads') {
      const r = await getLeads(params); data.value = r.leads || r || []; total.value = r.total || data.value.length
    } else {
      const r = await getPermits(params); data.value = r.permits || []; total.value = r.total || 0
    }
  } catch (e) { console.error('Load data error:', e) }
  finally { loading.value = false }
}

function switchDataset(id) {
  activeDataset.value = id; pagination.page = 1; sortKey.value = ''; resetFilters()
}
function resetFilters() {
  filters.search = ''; filters.city = ''; filters.minPrice = null; filters.maxPrice = null
  filters.isOwnerBuilder = null; filters.caseType = ''; filters.priority = ''; filters.status = ''
  pagination.page = 1; loadData()
}
function prevPage() { if (pagination.page > 1) { pagination.page--; loadData() } }
function nextPage() { if (pagination.page * pagination.limit < total.value) { pagination.page++; loadData() } }

function formatPrice(v) {
  if (!v) return '-'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v)
}
function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })
}
function priorityBadge(p) {
  if (p === 'RED') return 'badge-red'
  if (p === 'YELLOW') return 'badge-yellow'
  return 'badge-green'
}

onMounted(loadData)
</script>

<style scoped>
.hover-row {
  transition: background 0.1s;
}
.hover-row:hover {
  background: var(--bg-elevated);
}
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
