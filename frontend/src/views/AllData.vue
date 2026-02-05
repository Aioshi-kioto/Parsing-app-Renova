<template>
  <div class="space-y-6">
    <!-- Header with Tabs -->
    <div class="flex items-center justify-between">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-1 inline-flex">
        <button
          @click="activeDataset = 'zillow'"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeDataset === 'zillow' 
            ? 'bg-blue-100 text-blue-700' 
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'"
        >
          Zillow Homes
        </button>
        <button
          @click="activeDataset = 'permits'"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeDataset === 'permits' 
            ? 'bg-purple-100 text-purple-700' 
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'"
        >
          Building Permits
        </button>
      </div>

      <!-- Export Button -->
      <a 
        :href="exportUrl"
        class="px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors flex items-center gap-2"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
        Export CSV
      </a>
    </div>

    <!-- Stats Row -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Total Records</p>
        <p class="text-2xl font-bold text-gray-900">{{ stats.total || 0 }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">{{ activeDataset === 'zillow' ? 'Avg Price' : 'Avg Cost' }}</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.avg) }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">{{ activeDataset === 'zillow' ? 'Min Price' : 'Min Cost' }}</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.min) }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">{{ activeDataset === 'zillow' ? 'Max Price' : 'Max Cost' }}</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.max) }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-900">Filters</h3>
        <button 
          @click="resetFilters"
          class="text-sm text-gray-600 hover:text-gray-900"
        >
          Reset
        </button>
      </div>
      
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <!-- Search -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Search</label>
          <input 
            v-model="filters.search"
            type="text"
            placeholder="Address, ID..."
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <!-- City -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">City</label>
          <input 
            v-model="filters.city"
            type="text"
            placeholder="City name"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <!-- Min Price/Cost -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Min {{ activeDataset === 'zillow' ? 'Price' : 'Cost' }}
          </label>
          <input 
            v-model.number="filters.minPrice"
            type="number"
            placeholder="0"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <!-- Max Price/Cost -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Max {{ activeDataset === 'zillow' ? 'Price' : 'Cost' }}
          </label>
          <input 
            v-model.number="filters.maxPrice"
            type="number"
            placeholder="Any"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <!-- Permit-specific: Owner Builder -->
        <div v-if="activeDataset === 'permits'">
          <label class="block text-sm font-medium text-gray-700 mb-1">Owner-Builder</label>
          <select 
            v-model="filters.isOwnerBuilder"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          >
            <option :value="null">All</option>
            <option :value="true">Yes</option>
            <option :value="false">No</option>
          </select>
        </div>

        <!-- Zillow-specific: Beds -->
        <div v-if="activeDataset === 'zillow'">
          <label class="block text-sm font-medium text-gray-700 mb-1">Min Beds</label>
          <select 
            v-model="filters.minBeds"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option :value="null">Any</option>
            <option :value="1">1+</option>
            <option :value="2">2+</option>
            <option :value="3">3+</option>
            <option :value="4">4+</option>
            <option :value="5">5+</option>
          </select>
        </div>
      </div>

      <div class="mt-4 flex justify-end">
        <button 
          @click="loadData"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Apply Filters
        </button>
      </div>
    </div>

    <!-- Data Table -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200">
      <div v-if="loading" class="p-8 text-center text-gray-500">
        Loading data...
      </div>
      <div v-else-if="data.length === 0" class="p-8 text-center text-gray-500">
        No data found. Try adjusting your filters or start a parse job.
      </div>
      <div v-else class="overflow-x-auto">
        <!-- Zillow Table -->
        <table v-if="activeDataset === 'zillow'" class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ZPID</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Address</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">City</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Beds</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Baths</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sqft</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="home in data" :key="home.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm font-medium text-blue-600">
                <a :href="`https://zillow.com/homedetails/${home.zpid}_zpid/`" target="_blank" class="hover:underline">
                  {{ home.zpid }}
                </a>
              </td>
              <td class="px-4 py-3 text-sm text-gray-900">{{ home.address || 'N/A' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ home.city || 'N/A' }}</td>
              <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ formatPrice(home.price) }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ home.beds || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ home.baths || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ home.area_sqft ? `${home.area_sqft.toLocaleString()} sqft` : '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ home.home_type || '-' }}</td>
            </tr>
          </tbody>
        </table>

        <!-- Permits Table -->
        <table v-else class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Permit #</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Address</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cost</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Class</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Applied</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner-Builder</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="permit in data" :key="permit.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm font-medium text-purple-600">
                <a :href="permit.portal_link" target="_blank" class="hover:underline">
                  {{ permit.permit_num }}
                </a>
              </td>
              <td class="px-4 py-3 text-sm text-gray-900">{{ permit.address || 'N/A' }}</td>
              <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ formatPrice(permit.est_project_cost) }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ permit.permit_class || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ permit.applied_date || '-' }}</td>
              <td class="px-4 py-3">
                <span 
                  class="px-2 py-1 text-xs font-medium rounded-full"
                  :class="getOwnerBuilderClass(permit.is_owner_builder)"
                >
                  {{ getOwnerBuilderText(permit.is_owner_builder) }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ permit.status_current || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
        <div class="text-sm text-gray-500">
          Showing {{ (pagination.page - 1) * pagination.limit + 1 }} - {{ Math.min(pagination.page * pagination.limit, total) }} of {{ total }} results
        </div>
        <div class="flex items-center gap-2">
          <button 
            @click="prevPage"
            :disabled="pagination.page === 1"
            class="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Previous
          </button>
          <span class="text-sm text-gray-600">Page {{ pagination.page }}</span>
          <button 
            @click="nextPage"
            :disabled="pagination.page * pagination.limit >= total"
            class="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { 
  getZillowHomes, getZillowStats, getZillowExportAllUrl,
  getPermits, getPermitStats, getPermitExportAllUrl
} from '../api'

const activeDataset = ref('zillow')
const data = ref([])
const total = ref(0)
const loading = ref(false)

const stats = reactive({
  total: 0,
  avg: 0,
  min: 0,
  max: 0
})

const filters = reactive({
  search: '',
  city: '',
  minPrice: null,
  maxPrice: null,
  minBeds: null,
  isOwnerBuilder: null
})

const pagination = reactive({
  page: 1,
  limit: 50
})

const exportUrl = computed(() => {
  const params = buildFilterParams()
  if (activeDataset.value === 'zillow') {
    return getZillowExportAllUrl(params)
  } else {
    return getPermitExportAllUrl(params)
  }
})

function buildFilterParams() {
  const params = {}
  if (filters.search) params.search = filters.search
  if (filters.city) params.city = filters.city
  if (filters.minPrice) {
    params[activeDataset.value === 'zillow' ? 'min_price' : 'min_cost'] = filters.minPrice
  }
  if (filters.maxPrice) {
    params[activeDataset.value === 'zillow' ? 'max_price' : 'max_cost'] = filters.maxPrice
  }
  if (activeDataset.value === 'zillow' && filters.minBeds) {
    params.min_beds = filters.minBeds
  }
  if (activeDataset.value === 'permits' && filters.isOwnerBuilder !== null) {
    params.is_owner_builder = filters.isOwnerBuilder
  }
  return params
}

async function loadData() {
  loading.value = true
  try {
    const params = {
      ...buildFilterParams(),
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit
    }

    if (activeDataset.value === 'zillow') {
      const result = await getZillowHomes(params)
      data.value = result.homes || []
      total.value = result.total || 0
    } else {
      const result = await getPermits(params)
      data.value = result.permits || []
      total.value = result.total || 0
    }
  } catch (error) {
    console.error('Error loading data:', error)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    if (activeDataset.value === 'zillow') {
      const result = await getZillowStats()
      stats.total = result.total || 0
      stats.avg = result.avg_price || 0
      stats.min = result.min_price || 0
      stats.max = result.max_price || 0
    } else {
      const result = await getPermitStats()
      stats.total = result.total || 0
      stats.avg = result.avg_cost || 0
      stats.min = result.min_cost || 0
      stats.max = result.max_cost || 0
    }
  } catch (error) {
    console.error('Error loading stats:', error)
  }
}

function resetFilters() {
  filters.search = ''
  filters.city = ''
  filters.minPrice = null
  filters.maxPrice = null
  filters.minBeds = null
  filters.isOwnerBuilder = null
  pagination.page = 1
  loadData()
}

function prevPage() {
  if (pagination.page > 1) {
    pagination.page--
    loadData()
  }
}

function nextPage() {
  if (pagination.page * pagination.limit < total.value) {
    pagination.page++
    loadData()
  }
}

function formatPrice(value) {
  if (!value) return '-'
  return new Intl.NumberFormat('en-US', { 
    style: 'currency', 
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}

function getOwnerBuilderClass(isOwner) {
  if (isOwner === true) return 'bg-purple-100 text-purple-700'
  if (isOwner === false) return 'bg-gray-100 text-gray-600'
  return 'bg-amber-100 text-amber-700'
}

function getOwnerBuilderText(isOwner) {
  if (isOwner === true) return 'Yes'
  if (isOwner === false) return 'No'
  return 'Unknown'
}

watch(activeDataset, () => {
  pagination.page = 1
  resetFilters()
  loadStats()
})

onMounted(async () => {
  await Promise.all([loadData(), loadStats()])
})
</script>
