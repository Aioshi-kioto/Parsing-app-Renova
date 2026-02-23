<template>
  <div class="space-y-6">
    <!-- Header with Tabs -->
    <div class="flex items-center justify-between">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-1 inline-flex">
        <button
          @click="activeDataset = 'zillow'"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeDataset === 'zillow' 
            ? 'bg-gray-100 text-gray-900' 
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'"
        >
          Zillow Homes
        </button>
        <button
          @click="activeDataset = 'permits'"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeDataset === 'permits' 
            ? 'bg-gray-100 text-gray-900' 
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'"
        >
          Building Permits
        </button>
        <button
          @click="activeDataset = 'mbp'"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeDataset === 'mbp' 
            ? 'bg-purple-100 text-purple-900' 
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'"
        >
          MyBuildingPermit
        </button>
      </div>

      <!-- Export Buttons: MBP и Permits — 4 кнопки (All/Owners), Zillow — 2 -->
      <div class="flex items-center gap-2 flex-wrap">
        <template v-if="activeDataset === 'mbp'">
          <a :href="getMBPExportUrl(null, 'csv', false)" class="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 border border-gray-300" download>All CSV</a>
          <a :href="getMBPExportUrl(null, 'xlsx', false)" class="px-3 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700" download>All Excel</a>
          <a :href="getMBPExportUrl(null, 'csv', true)" class="px-3 py-2 bg-purple-100 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-200 border border-purple-300" download>Owners CSV</a>
          <a :href="getMBPExportUrl(null, 'xlsx', true)" class="px-3 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700" download>Owners Excel</a>
        </template>
        <template v-else-if="activeDataset === 'permits'">
          <a :href="getPermitExportAllUrl({ ...buildFilterParams(), format: 'csv' })" class="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 border border-gray-300" download>All CSV</a>
          <a :href="getPermitExportAllUrl({ ...buildFilterParams(), format: 'xlsx' })" class="px-3 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700" download>All Excel</a>
          <a :href="getPermitExportAllUrl({ ...buildFilterParams(), format: 'csv', is_owner_builder: true })" class="px-3 py-2 bg-teal-100 text-teal-700 rounded-lg text-sm font-medium hover:bg-teal-200 border border-teal-300" download>Owners CSV</a>
          <a :href="getPermitExportAllUrl({ ...buildFilterParams(), format: 'xlsx', is_owner_builder: true })" class="px-3 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700" download>Owners Excel</a>
        </template>
        <template v-else>
          <a :href="exportCsvUrl" class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 border border-gray-300 flex items-center gap-2" download>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            Export CSV
          </a>
          <a :href="exportExcelUrl" class="px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 flex items-center gap-2" download>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
            Export Excel
          </a>
        </template>
      </div>
    </div>

    <!-- Stats Row: для MBP — Total / Matching types / Owner-builders (from matching) -->
    <div v-if="activeDataset === 'mbp'" class="grid grid-cols-1 md:grid-cols-3 gap-4">
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
    <!-- Permits: Total, Owner-Builders, Avg/Min/Max Cost -->
    <div v-else-if="activeDataset === 'permits'" class="grid grid-cols-2 md:grid-cols-5 gap-4">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Total Records</p>
        <p class="text-2xl font-bold text-gray-900">{{ stats.total || 0 }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-teal-200 p-4">
        <p class="text-sm text-teal-600">Owner-Builders</p>
        <p class="text-2xl font-bold text-teal-700">{{ stats.owner_builders || 0 }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Avg Cost</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.avg) }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Min Cost</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.min) }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Max Cost</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.max) }}</p>
      </div>
    </div>
    <!-- Zillow: Total, Avg/Min/Max Price -->
    <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Total Records</p>
        <p class="text-2xl font-bold text-gray-900">{{ stats.total || 0 }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Avg Price</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.avg) }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Min Price</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.min) }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Max Price</p>
        <p class="text-2xl font-bold text-gray-900">{{ formatPrice(stats.max) }}</p>
      </div>
    </div>

    <!-- MBP: By permit type (для проверки в Excel) -->
    <div v-if="activeDataset === 'mbp' && stats.by_type && Object.keys(stats.by_type).length > 0" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 class="text-sm font-semibold text-gray-700 mb-3">By permit type</h3>
      <div class="overflow-x-auto max-h-48 overflow-y-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-gray-200">
              <th class="text-left py-2 font-medium text-gray-600">Type</th>
              <th class="text-right py-2 font-medium text-gray-600">Count</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(count, typeName) in stats.by_type" :key="typeName" class="border-b border-gray-100">
              <td class="py-1.5 text-gray-800">{{ typeName }}</td>
              <td class="py-1.5 text-right font-medium text-gray-900">{{ count }}</td>
            </tr>
          </tbody>
        </table>
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
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
          />
        </div>

        <!-- City -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">City</label>
          <input 
            v-model="filters.city"
            type="text"
            placeholder="City name"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
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
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
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
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
          />
        </div>

        <!-- Permit / MBP: Owner-Builder filter -->
        <div v-if="activeDataset === 'permits' || activeDataset === 'mbp'">
          <label class="block text-sm font-medium text-gray-700 mb-1">Owner-Builder</label>
          <select 
            v-model="filters.isOwnerBuilder"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
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
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
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
        <!-- Zillow Table: все вытащенные поля -->
        <div v-if="activeDataset === 'zillow'" class="overflow-x-auto rounded-lg border border-gray-200">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-blue-50">
              <tr>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">ZPID</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Address</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">City</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">State</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Zip</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Price</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Beds</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Baths</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Sqft</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Type</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Year</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Zestimate</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Tax Value</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-blue-800 uppercase tracking-wider">Sold</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="home in data" :key="home.id" class="hover:bg-blue-50/50 transition-colors">
                <td class="px-3 py-2.5 text-sm font-medium text-blue-700 whitespace-nowrap">
                  <a :href="home.detail_url || `https://zillow.com/homedetails/${home.zpid}_zpid/`" target="_blank" rel="noopener" class="hover:underline">
                    {{ home.zpid || '—' }}
                  </a>
                </td>
                <td class="px-3 py-2.5 text-sm text-gray-800 max-w-[180px] truncate" :title="home.address">{{ home.address || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-700">{{ home.city || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ home.state || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ home.zipcode || '—' }}</td>
                <td class="px-3 py-2.5 text-sm font-medium text-gray-900">{{ formatPrice(home.price) }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ home.beds ?? '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ home.baths ?? '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ home.area_sqft ? `${home.area_sqft.toLocaleString()} sqft` : '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ home.home_type || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ home.year_built || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ formatPrice(home.zestimate) }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ formatPrice(home.tax_assessed_value) }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600 whitespace-nowrap">{{ home.date_sold || home.sold_date_text || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Building Permits Table: все вытащенные поля (master_spec) -->
        <div v-else-if="activeDataset === 'permits'" class="overflow-x-auto rounded-lg border border-gray-200">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-teal-50">
              <tr>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Permit #</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Address</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">City</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">State</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Zip</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Description</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Cost</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Class</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Type</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Applied</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Issued</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Status</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Contractor</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Verification</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Work Performer</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-teal-800 uppercase tracking-wider">Owner-Builder</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="permit in data" :key="permit.id" class="hover:bg-teal-50/50 transition-colors">
                <td class="px-3 py-2.5 text-sm font-medium text-teal-700 whitespace-nowrap">
                  <a :href="permit.portal_link" target="_blank" rel="noopener" class="hover:underline">
                    {{ permit.permit_num || '—' }}
                  </a>
                </td>
                <td class="px-3 py-2.5 text-sm text-gray-800 max-w-[160px] truncate" :title="permit.address">{{ permit.address || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-700">{{ permit.city || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ permit.state || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ permit.zipcode || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-700 max-w-[200px] truncate" :title="permit.description">{{ permit.description || '—' }}</td>
                <td class="px-3 py-2.5 text-sm font-medium text-gray-900">{{ formatPrice(permit.est_project_cost) }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ permit.permit_class || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600 max-w-[100px] truncate" :title="permit.permit_type_desc || permit.permit_type_mapped">{{ permit.permit_type_mapped || permit.permit_type_desc || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600 whitespace-nowrap">{{ permit.applied_date || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600 whitespace-nowrap">{{ permit.issued_date || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ permit.status_current || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-700 max-w-[120px] truncate" :title="permit.contractor_name">{{ permit.contractor_name || '—' }}</td>
                <td class="px-3 py-2.5 text-sm" :class="permit.verification_status === 'error' ? 'text-red-600' : 'text-gray-600'" :title="permit.verification_status === 'error' ? (permit.work_performer_text || 'Verification did not run') : ''">{{ permit.verification_status === 'error' ? 'Error' : (permit.verification_status || '—') }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600 max-w-[120px] truncate" :title="permit.work_performer_text">{{ permit.work_performer_text || '—' }}</td>
                <td class="px-3 py-2.5">
                  <span 
                    class="px-2 py-0.5 text-xs font-medium rounded-full"
                    :class="getOwnerBuilderClass(permit.is_owner_builder)"
                    :title="permit.work_performer_text || ''"
                  >
                    {{ getOwnerBuilderText(permit.is_owner_builder, permit.work_performer_text) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- MyBuildingPermit Table: все вытащенные поля -->
        <div v-else class="overflow-x-auto rounded-lg border border-gray-200">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-purple-50">
              <tr>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Permit #</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Jurisdiction</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Project</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Address</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Type</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Status</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Applied</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Issued</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Applicant</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Contractor</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">License</th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-purple-800 uppercase tracking-wider">Owner-Builder</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="permit in data" :key="permit.id" class="hover:bg-purple-50/50 transition-colors">
                <td class="px-3 py-2.5 text-sm font-medium text-purple-700 whitespace-nowrap">
                  <a :href="permit.permit_url" target="_blank" rel="noopener" class="hover:underline">
                    {{ permit.permit_number || '—' }}
                  </a>
                </td>
                <td class="px-3 py-2.5 text-sm text-gray-700">{{ permit.jurisdiction || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-800 max-w-[200px] truncate" :title="permit.project_name">{{ permit.project_name || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-800 max-w-[180px] truncate" :title="permit.address">{{ permit.address || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ permit.permit_type || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600">{{ permit.permit_status || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600 whitespace-nowrap">{{ permit.applied_date || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600 whitespace-nowrap">{{ permit.issued_date || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-700 max-w-[140px] truncate" :title="permit.applicant_name">{{ permit.applicant_name || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-700 max-w-[140px] truncate" :title="permit.contractor_name">{{ permit.contractor_name || '—' }}</td>
                <td class="px-3 py-2.5 text-sm text-gray-600 font-mono">{{ permit.contractor_license || '—' }}</td>
                <td class="px-3 py-2.5">
                  <span 
                    class="px-2 py-0.5 text-xs font-medium rounded-full"
                    :class="getOwnerBuilderClass(permit.is_owner_builder)"
                  >
                    {{ getOwnerBuilderTextMBP(permit.is_owner_builder) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
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
  getPermits, getPermitStats, getPermitExportAllUrl,
  getMBPPermits, getMBPStats, getMBPExportUrl
} from '../api'

const activeDataset = ref('zillow')
const data = ref([])
const total = ref(0)
const loading = ref(false)

const stats = reactive({
  total: 0,
  avg: 0,
  min: 0,
  max: 0,
  owner_builders: 0,
  matching_types: 0,
  owner_builders_from_matching: 0,
  by_type: {},
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

const exportCsvUrl = computed(() => {
  if (activeDataset.value === 'zillow') {
    return getZillowExportAllUrl({ ...buildFilterParams(), format: 'csv' })
  }
  if (activeDataset.value === 'mbp') {
    return getMBPExportUrl(null, 'csv', filters.isOwnerBuilder === true)
  }
  return getPermitExportAllUrl({ ...buildFilterParams(), format: 'csv' })
})

const exportExcelUrl = computed(() => {
  if (activeDataset.value === 'zillow') {
    return getZillowExportAllUrl({ ...buildFilterParams(), format: 'xlsx' })
  }
  if (activeDataset.value === 'mbp') {
    return getMBPExportUrl(null, 'xlsx', filters.isOwnerBuilder === true)
  }
  return getPermitExportAllUrl({ ...buildFilterParams(), format: 'xlsx' })
})

function buildFilterParams() {
  const params = {}
  if (filters.search) params.search = filters.search
  if (filters.city && activeDataset.value !== 'mbp') params.city = filters.city
  if (filters.city && activeDataset.value === 'mbp') params.jurisdiction = filters.city
  if (filters.minPrice && activeDataset.value !== 'mbp') {
    params[activeDataset.value === 'zillow' ? 'min_price' : 'min_cost'] = filters.minPrice
  }
  if (filters.maxPrice && activeDataset.value !== 'mbp') {
    params[activeDataset.value === 'zillow' ? 'max_price' : 'max_cost'] = filters.maxPrice
  }
  if (activeDataset.value === 'zillow' && filters.minBeds) {
    params.min_beds = filters.minBeds
  }
  if ((activeDataset.value === 'permits' || activeDataset.value === 'mbp') && filters.isOwnerBuilder !== null) {
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
    } else if (activeDataset.value === 'mbp') {
      const result = await getMBPPermits({
        ...params,
        skip: (pagination.page - 1) * pagination.limit,
        limit: pagination.limit,
        is_owner_builder: filters.isOwnerBuilder === true ? true : filters.isOwnerBuilder === false ? false : undefined
      })
      data.value = result.permits || []
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
    } else if (activeDataset.value === 'mbp') {
      const result = await getMBPStats()
      stats.total = result.total || 0
      stats.matching_types = result.matching_types || 0
      stats.owner_builders_from_matching = result.owner_builders_from_matching || 0
      stats.by_type = result.by_type || {}
      stats.avg = 0
      stats.min = 0
      stats.max = 0
    } else {
      const result = await getPermitStats()
      stats.total = result.total || 0
      stats.owner_builders = result.owner_builders || 0
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
  if (isOwner === true) return 'bg-gray-900 text-white'
  if (isOwner === false) return 'bg-gray-100 text-gray-600'
  return 'bg-amber-100 text-amber-700'
}

function getOwnerBuilderText(isOwner, workPerformerText) {
  // Если есть work_performer_text (конкретный текст из верификации) - показываем его
  if (workPerformerText && workPerformerText !== 'Not found' && workPerformerText !== 'N/A') {
    // Обрезаем длинный текст
    return workPerformerText.length > 30 ? workPerformerText.substring(0, 30) + '...' : workPerformerText
  }
  // Иначе показываем Yes/No/Unknown
  if (isOwner === true) return 'Yes'
  if (isOwner === false) return 'No'
  return 'Unknown'
}

function getOwnerBuilderTextMBP(isOwner) {
  if (isOwner === true) return 'Yes'
  if (isOwner === false) return 'No'
  return '—'
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
