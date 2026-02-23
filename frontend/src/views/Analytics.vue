<template>
  <div class="space-y-6">
    <!-- Tabs -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-1 inline-flex">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        :class="activeTab === tab.id 
          ? 'bg-gray-100 text-gray-900' 
          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'"
      >
        {{ tab.name }}
      </button>
    </div>

    <!-- KPI Cards: для MBP — Total / Matching / Owner-builders; для остальных — стандартные -->
    <div v-if="activeTab === 'mbp'" class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Total Analyzed</p>
        <p class="text-2xl font-bold text-gray-900">{{ stats.total || 0 }}</p>
        <p class="text-xs text-gray-400 mt-1">Все пермиты без фильтра</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-purple-200 p-4">
        <p class="text-sm text-purple-600">Matching Types</p>
        <p class="text-2xl font-bold text-purple-700">{{ stats.matching_types || 0 }}</p>
        <p class="text-xs text-gray-400 mt-1">Подходят под TARGET_CONFIG</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-purple-200 p-4">
        <p class="text-sm text-purple-600">Owner-Builders</p>
        <p class="text-2xl font-bold text-purple-700">{{ stats.owner_builders_from_matching || 0 }}</p>
        <p class="text-xs text-gray-400 mt-1">Из matching types</p>
      </div>
    </div>
    <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">{{ activeTab === 'zillow' ? 'Total Homes' : 'Total Permits' }}</p>
        <p class="text-2xl font-bold text-gray-900">{{ stats.total || 0 }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">{{ activeTab === 'zillow' ? 'Avg Price' : 'Avg Cost' }}</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.avg_value) }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">{{ activeTab === 'zillow' ? 'Unique' : 'Owner-Builders' }}</p>
        <p class="text-2xl font-bold text-gray-900">{{ stats.secondary || 0 }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Total Value</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.total_value) }}</p>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Price/Cost Distribution -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          {{ activeTab === 'zillow' ? 'Price Distribution' : activeTab === 'mbp' ? 'By Jurisdiction' : 'Cost Distribution' }}
        </h3>
        <div class="h-64">
          <canvas ref="distributionChart"></canvas>
        </div>
      </div>

      <!-- Timeline -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Timeline</h3>
        <div class="h-64">
          <canvas ref="timelineChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Second Row: Pie + Bar -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Pie Chart -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          {{ activeTab === 'zillow' ? 'Home Types' : activeTab === 'mbp' ? 'Owner-Builder Ratio' : 'Owner-Builder Ratio' }}
        </h3>
        <div class="h-64 flex items-center justify-center">
          <canvas ref="pieChart"></canvas>
        </div>
      </div>

      <!-- By City/Class -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          {{ activeTab === 'zillow' ? 'Top Cities' : 'By Permit Class' }}
        </h3>
        <div class="h-64">
          <canvas ref="barChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Map Section -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-900">Map View</h3>
        <div class="flex items-center gap-2">
          <label class="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" v-model="showZillowMarkers" class="rounded text-gray-900" />
            Zillow Homes
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" v-model="showPermitMarkers" class="rounded text-purple-600" />
            Permits
          </label>
        </div>
      </div>
      <div ref="mapContainer" class="h-96 rounded-lg bg-gray-100"></div>
      <p v-if="!mapInitialized" class="text-center py-8 text-gray-500">
        Map requires Leaflet. Run: npm install leaflet @vue-leaflet/vue-leaflet
      </p>
    </div>

    <!-- Data Summary Table -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">
        {{ activeTab === 'zillow' ? 'Top Cities Summary' : activeTab === 'mbp' ? 'Jurisdiction Summary' : 'Permit Class Summary' }}
      </h3>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ activeTab === 'zillow' ? 'City' : 'Class' }}
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Count</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ activeTab === 'zillow' ? 'Avg Price' : 'Percentage' }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="(item, index) in summaryData" :key="index" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ item.label }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ item.count }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ activeTab === 'zillow' ? formatPrice(item.value) : `${item.percentage}%` }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import {
  getZillowStats, getZillowPriceDistribution, getZillowTimeline, getZillowByCity, getZillowHomeTypes,
  getPermitStats, getPermitsCostDistribution, getPermitsTimeline, getOwnerBuilderRatio, getPermitsByClass,
  getMapZillowHomes, getMapPermits,
  getMBPStats
} from '../api'

// Tabs
const tabs = [
  { id: 'zillow', name: 'Zillow Analytics' },
  { id: 'permits', name: 'Permits Analytics' },
  { id: 'mbp', name: 'MyBuildingPermit Analytics' }
]
const activeTab = ref('zillow')

// Chart refs
const distributionChart = ref(null)
const timelineChart = ref(null)
const pieChart = ref(null)
const barChart = ref(null)
const mapContainer = ref(null)

// Chart instances
let distributionChartInstance = null
let timelineChartInstance = null
let pieChartInstance = null
let barChartInstance = null
let mapInstance = null
const mapInitialized = ref(false)

// Map markers
const showZillowMarkers = ref(true)
const showPermitMarkers = ref(true)

// Data
const stats = reactive({
  total: 0,
  avg_value: 0,
  secondary: 0,
  total_value: 0
})

const summaryData = ref([])

// Colors
const colors = {
  blue: 'rgb(59, 130, 246)',
  blueLight: 'rgba(59, 130, 246, 0.2)',
  purple: 'rgb(147, 51, 234)',
  purpleLight: 'rgba(147, 51, 234, 0.2)',
  green: 'rgb(34, 197, 94)',
  amber: 'rgb(245, 158, 11)',
  red: 'rgb(239, 68, 68)',
  gray: 'rgb(107, 114, 128)'
}

function formatPrice(value) {
  if (!value) return '$0'
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`
  }
  return `$${value.toFixed(0)}`
}

async function loadZillowData() {
  try {
    // Stats
    const zillowStats = await getZillowStats()
    stats.total = zillowStats.total || 0
    stats.avg_value = zillowStats.avg_price || 0
    stats.secondary = zillowStats.unique_count || 0
    stats.total_value = (zillowStats.avg_price || 0) * (zillowStats.total || 0)

    // Distribution chart
    const distribution = await getZillowPriceDistribution(null, 8)
    updateDistributionChart(distribution)

    // Timeline chart
    const timeline = await getZillowTimeline(30)
    updateTimelineChart(timeline)

    // Home types (pie)
    const homeTypes = await getZillowHomeTypes()
    updatePieChart(homeTypes)

    // By city (bar)
    const byCity = await getZillowByCity(8)
    updateBarChart(byCity.map(c => ({ label: c.city, count: c.count, value: c.avg_price })))
    summaryData.value = byCity.map(c => ({
      label: c.city,
      count: c.count,
      value: c.avg_price,
      percentage: 0
    }))

  } catch (error) {
    console.error('Error loading Zillow data:', error)
  }
}

async function loadPermitsData() {
  try {
    // Stats
    const permitStats = await getPermitStats()
    stats.total = permitStats.total || 0
    stats.avg_value = permitStats.avg_cost || 0
    stats.secondary = permitStats.owner_builders || 0
    stats.total_value = permitStats.total_cost || 0

    // Distribution chart
    const distribution = await getPermitsCostDistribution(null, 8)
    updateDistributionChart(distribution)

    // Timeline chart
    const timeline = await getPermitsTimeline(90)
    updateTimelineChart(timeline)

    // Owner-builder ratio (pie)
    const ratio = await getOwnerBuilderRatio()
    updatePieChart(ratio)

    // By class (bar)
    const byClass = await getPermitsByClass()
    updateBarChart(byClass.map(c => ({ label: c.label, count: c.count })))
    summaryData.value = byClass.map(c => ({
      label: c.label,
      count: c.count,
      percentage: c.percentage
    }))

  } catch (error) {
    console.error('Error loading Permits data:', error)
  }
}

async function loadMBPData() {
  try {
    // Stats
    const mbpStats = await getMBPStats()
    stats.total = mbpStats.total || 0
    stats.matching_types = mbpStats.matching_types || 0
    stats.owner_builders_from_matching = mbpStats.owner_builders_from_matching || 0
    stats.avg_value = 0
    stats.secondary = mbpStats.owner_builders || 0
    stats.total_value = 0

    // By jurisdiction (bar)
    const byJurisdiction = Object.entries(mbpStats.by_jurisdiction || {}).map(([jurisdiction, count]) => ({
      label: jurisdiction,
      count: count
    }))
    updateBarChart(byJurisdiction)
    summaryData.value = byJurisdiction.map(j => ({
      label: j.label,
      count: j.count,
      percentage: 0
    }))

    // Owner-builder ratio (pie)
    const total = mbpStats.total || 0
    const owners = mbpStats.owner_builders || 0
    const contractors = total - owners
    updatePieChart([
      { label: 'Owner-Builder', count: owners },
      { label: 'Licensed Contractor', count: contractors }
    ])

    // Empty charts for now (MBP doesn't have cost/timeline data)
    updateDistributionChart([])
    updateTimelineChart([])

  } catch (error) {
    console.error('Error loading MBP data:', error)
  }
}

function updateDistributionChart(data) {
  if (!distributionChart.value) return
  
  const ctx = distributionChart.value.getContext('2d')
  if (distributionChartInstance) {
    distributionChartInstance.destroy()
  }

  import('chart.js').then(({ Chart, registerables }) => {
    Chart.register(...registerables)
    
    distributionChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.label),
        datasets: [{
          label: 'Count',
          data: data.map(d => d.count),
          backgroundColor: activeTab.value === 'zillow' ? colors.blueLight : colors.purpleLight,
          borderColor: activeTab.value === 'zillow' ? colors.blue : colors.purple,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true }
        }
      }
    })
  })
}

function updateTimelineChart(data) {
  if (!timelineChart.value) return
  
  const ctx = timelineChart.value.getContext('2d')
  if (timelineChartInstance) {
    timelineChartInstance.destroy()
  }

  import('chart.js').then(({ Chart, registerables }) => {
    Chart.register(...registerables)
    
    timelineChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.map(d => d.date),
        datasets: [{
          label: 'Count',
          data: data.map(d => d.count),
          borderColor: activeTab.value === 'zillow' ? colors.blue : colors.purple,
          backgroundColor: activeTab.value === 'zillow' ? colors.blueLight : colors.purpleLight,
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true }
        }
      }
    })
  })
}

function updatePieChart(data) {
  if (!pieChart.value) return
  
  const ctx = pieChart.value.getContext('2d')
  if (pieChartInstance) {
    pieChartInstance.destroy()
  }

  import('chart.js').then(({ Chart, registerables }) => {
    Chart.register(...registerables)
    
    pieChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.map(d => d.label),
        datasets: [{
          data: data.map(d => d.count),
          backgroundColor: [colors.blue, colors.purple, colors.green, colors.amber, colors.red, colors.gray],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right'
          }
        }
      }
    })
  })
}

function updateBarChart(data) {
  if (!barChart.value) return
  
  const ctx = barChart.value.getContext('2d')
  if (barChartInstance) {
    barChartInstance.destroy()
  }

  import('chart.js').then(({ Chart, registerables }) => {
    Chart.register(...registerables)
    
    barChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.label),
        datasets: [{
          label: 'Count',
          data: data.map(d => d.count),
          backgroundColor: activeTab.value === 'zillow' ? colors.blue : colors.purple,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true }
        }
      }
    })
  })
}

async function initMap() {
  if (!mapContainer.value) return
  
  try {
    const L = await import('leaflet')
    await import('leaflet/dist/leaflet.css')
    
    // Fix default marker icons
    delete L.Icon.Default.prototype._getIconUrl
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
      iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png'
    })
    
    mapInstance = L.map(mapContainer.value).setView([47.6062, -122.3321], 10)
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(mapInstance)
    
    mapInitialized.value = true
    await loadMapMarkers()
  } catch (error) {
    console.error('Error initializing map:', error)
    mapInitialized.value = false
  }
}

async function loadMapMarkers() {
  if (!mapInstance) return
  
  try {
    const L = await import('leaflet')
    
    // Clear existing markers
    mapInstance.eachLayer(layer => {
      if (layer instanceof L.Marker) {
        mapInstance.removeLayer(layer)
      }
    })
    
    // Load and add markers
    if (showZillowMarkers.value) {
      const zillowData = await getMapZillowHomes(null, 200)
      zillowData.markers?.forEach(m => {
        if (m.latitude && m.longitude) {
          const marker = L.marker([m.latitude, m.longitude])
            .bindPopup(`<b>${m.title}</b><br>${m.address || 'N/A'}`)
          marker.addTo(mapInstance)
        }
      })
    }
    
    if (showPermitMarkers.value) {
      const permitData = await getMapPermits(null, null, 200)
      permitData.markers?.forEach(m => {
        if (m.latitude && m.longitude) {
          const marker = L.marker([m.latitude, m.longitude], {
            icon: L.divIcon({
              className: 'bg-gray-900 w-3 h-3 rounded-full border-2 border-white',
              iconSize: [12, 12]
            })
          }).bindPopup(`<b>${m.title}</b><br>${m.address || 'N/A'}`)
          marker.addTo(mapInstance)
        }
      })
    }
  } catch (error) {
    console.error('Error loading map markers:', error)
  }
}

watch(activeTab, async () => {
  await nextTick()
  if (activeTab.value === 'zillow') {
    await loadZillowData()
  } else if (activeTab.value === 'mbp') {
    await loadMBPData()
  } else {
    await loadPermitsData()
  }
})

watch([showZillowMarkers, showPermitMarkers], () => {
  if (mapInitialized.value) {
    loadMapMarkers()
  }
})

onMounted(async () => {
  await loadZillowData()
  await initMap()
})

onUnmounted(() => {
  if (distributionChartInstance) distributionChartInstance.destroy()
  if (timelineChartInstance) timelineChartInstance.destroy()
  if (pieChartInstance) pieChartInstance.destroy()
  if (barChartInstance) barChartInstance.destroy()
  if (mapInstance) mapInstance.remove()
})
</script>

<style>
@import 'leaflet/dist/leaflet.css';
</style>
