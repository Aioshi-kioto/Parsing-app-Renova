<template>
  <div class="space-y-6">
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Zillow Homes -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-500">Zillow Homes</p>
            <p class="text-2xl font-bold text-gray-900 mt-1">{{ numberOrZero(stats.zillow?.total_homes) }}</p>
            <p class="text-sm text-gray-500 mt-1">
              {{ numberOrZero(stats.zillow?.unique_homes) }} unique
            </p>
          </div>
          <div class="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Avg Home Price (Zillow) -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-500">Avg Home Price</p>
            <p class="text-2xl font-bold text-gray-900 mt-1">{{ formatPrice(stats.zillow?.avg_price) }}</p>
            <p class="text-sm text-gray-500 mt-1">Zillow data</p>
          </div>
          <div class="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Building Permits (Seattle) -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-500">Building Permits</p>
            <p class="text-2xl font-bold text-gray-900 mt-1">{{ numberOrZero(stats.permits?.total_permits) }}</p>
            <p class="text-sm text-gray-500 mt-1">
              {{ numberOrZero(stats.permits?.owner_builders) }} owner-builders · {{ formatPrice(stats.permits?.total_project_cost) }} total
            </p>
          </div>
          <div class="w-12 h-12 bg-teal-100 rounded-xl flex items-center justify-center">
            <svg class="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- MyBuildingPermit -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-500">MyBuildingPermit</p>
            <p class="text-2xl font-bold text-gray-900 mt-1">{{ numberOrZero(stats.mbp?.total_permits) }}</p>
            <p class="text-sm text-gray-500 mt-1">
              {{ numberOrZero(stats.mbp?.owner_builders) }} owner-builders
            </p>
          </div>
          <div class="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Quick Actions Card -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div class="grid grid-cols-2 gap-4">
          <router-link 
            to="/zillow" 
            class="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
          >
            <div class="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
              </svg>
            </div>
            <div>
              <p class="font-medium text-gray-900">New Zillow Parse</p>
              <p class="text-sm text-gray-500">Parse homes from URLs</p>
            </div>
          </router-link>

          <router-link 
            to="/permits" 
            class="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-colors"
          >
            <div class="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
              </svg>
            </div>
            <div>
              <p class="font-medium text-gray-900">New Permit Parse</p>
              <p class="text-sm text-gray-500">Find owner-builders</p>
            </div>
          </router-link>

          <router-link 
            to="/mybuildingpermit" 
            class="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-purple-300 hover:bg-purple-50 transition-colors"
          >
            <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
              </svg>
            </div>
            <div>
              <p class="font-medium text-gray-900">MyBuildingPermit</p>
              <p class="text-sm text-gray-500">Parse WA permits</p>
            </div>
          </router-link>

          <router-link 
            to="/analytics" 
            class="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-green-300 hover:bg-green-50 transition-colors"
          >
            <div class="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
            </div>
            <div>
              <p class="font-medium text-gray-900">View Analytics</p>
              <p class="text-sm text-gray-500">Charts and maps</p>
            </div>
          </router-link>

          <router-link 
            to="/data" 
            class="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-amber-300 hover:bg-amber-50 transition-colors"
          >
            <div class="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
              </svg>
            </div>
            <div>
              <p class="font-medium text-gray-900">Export Data</p>
              <p class="text-sm text-gray-500">Download CSV/Excel</p>
            </div>
          </router-link>
        </div>
      </div>

      <!-- Recent Jobs -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Recent Jobs</h2>
        <div class="space-y-3">
          <div v-if="stats.recent_jobs?.length === 0" class="text-center py-8 text-gray-500">
            No recent jobs. Start a new parse to see activity here.
          </div>
          <div 
            v-for="job in stats.recent_jobs" 
            :key="`${job.type}-${job.id}`"
            class="flex items-center justify-between p-3 rounded-lg bg-gray-50"
          >
            <div class="flex items-center gap-3">
              <div 
                class="w-8 h-8 rounded-lg flex items-center justify-center"
                :class="job.type === 'zillow' ? 'bg-gray-100' : 'bg-gray-100'"
              >
                <span class="text-xs font-bold" :class="job.type === 'zillow' ? 'text-blue-600' : job.type === 'mbp' ? 'text-purple-600' : 'text-gray-900'">
                  {{ job.type === 'zillow' ? 'Z' : job.type === 'mbp' ? 'MBP' : 'P' }}
                </span>
              </div>
              <div>
                <p class="text-sm font-medium text-gray-900">
                  {{ jobLabel(job.type) }} #{{ job.id }}
                </p>
                <p class="text-xs text-gray-500">{{ formatDate(job.started_at) }}</p>
              </div>
            </div>
            <span 
              class="px-2 py-1 text-xs font-medium rounded-full"
              :class="getStatusClass(job.status)"
            >
              {{ job.status }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Info Banner -->
    <div class="bg-gray-900 rounded-xl p-6 text-white">
      <div>
        <h3 class="text-lg font-semibold">Renova Parse CRM</h3>
        <p class="text-blue-100 mt-1">
          Unified platform for parsing Zillow real estate data, Seattle building permits, and MyBuildingPermit.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getOverviewStats } from '../api'

const stats = ref({
  zillow: {},
  permits: {},
  recent_jobs: []
})

const loading = ref(true)

async function loadStats() {
  try {
    loading.value = true
    stats.value = await getOverviewStats()
  } catch (error) {
    console.error('Failed to load stats:', error)
  } finally {
    loading.value = false
  }
}

function numberOrZero(val) {
  const n = Number(val)
  return Number.isFinite(n) ? n : 0
}

function formatPrice(value) {
  const n = Number(value)
  if (!Number.isFinite(n) || n === 0) return '—'
  return new Intl.NumberFormat('en-US', { 
    style: 'currency', 
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(n)
}

function jobLabel(type) {
  if (type === 'zillow') return 'Zillow Parse'
  if (type === 'mbp') return 'MyBuildingPermit'
  return 'Permit Parse'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getStatusClass(status) {
  const classes = {
    completed: 'bg-green-100 text-green-700',
    running: 'bg-gray-100 text-blue-700',
    pending: 'bg-gray-100 text-gray-700',
    failed: 'bg-red-100 text-red-700',
    parsing: 'bg-gray-100 text-gray-700',
    verifying: 'bg-amber-100 text-amber-700',
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

onMounted(loadStats)
</script>
