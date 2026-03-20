<template>
  <div class="space-y-5 animate-fadeIn">
    <div>
      <div class="text-[10px] mb-1" style="color: var(--text-muted);">/аналитика/обзор</div>
      <h1 class="text-xl font-bold tracking-wide" style="color: var(--text-primary);">АНАЛИТИКА</h1>
    </div>

    <div class="flex gap-0 border-b" style="border-color: var(--border);">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="terminal-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- BILLING TAB -->
    <template v-if="activeTab === 'billing'">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
        <div v-for="prov in providerOrder" :key="prov" class="card p-4 relative overflow-hidden">
          <div class="absolute top-0 right-0 p-2 opacity-10">
            <div class="text-4xl font-bold uppercase">{{ prov[0] }}</div>
          </div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-[10px] font-semibold tracking-widest uppercase" style="color: var(--text-secondary);">{{ providerLabels[prov] || prov }}</span>
            <span v-if="prov === 'sms_beta'" class="text-[8px] px-1 py-0.5 rounded" style="background: var(--accent-yellow); color: #000;">BETA</span>
            <span v-if="billingData[prov]?.status === 'warning'" class="text-[8px] px-1 py-0.5 rounded" style="background: var(--accent-yellow); color: #000;">ВНИМАНИЕ</span>
            <span v-if="billingData[prov]?.status === 'over_budget'" class="text-[8px] px-1 py-0.5 rounded" style="background: var(--accent-red); color: #fff;">ПРЕВЫШЕН</span>
          </div>
          <div class="text-2xl font-bold mb-1" style="color: var(--text-primary);">${{ (billingData[prov]?.estimated_cost || 0).toFixed(2) }}</div>
          <div class="text-[10px]" style="color: var(--text-muted);">расходы за месяц</div>

          <div class="mt-3 pt-3 border-t space-y-1" style="border-color: var(--border);">
            <div class="flex justify-between items-center">
              <span class="text-[10px]" style="color: var(--text-muted);">событий</span>
              <span class="text-[10px] font-bold" style="color: var(--accent-cyan);">{{ billingData[prov]?.success_count || 0 }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-[10px]" style="color: var(--text-muted);">тариф</span>
              <span class="text-[10px]" style="color: var(--text-primary);">${{ billingData[prov]?.unit_cost_usd || 0 }}/{{ billingData[prov]?.unit_name || '?' }}</span>
            </div>
            <div v-if="billingData[prov]?.budget_usd > 0" class="flex justify-between items-center">
              <span class="text-[10px]" style="color: var(--text-muted);">бюджет</span>
              <span class="text-[10px]" style="color: var(--text-primary);">
                ${{ billingData[prov]?.remaining_usd?.toFixed(2) }} / ${{ billingData[prov]?.budget_usd?.toFixed(2) }}
                ({{ billingData[prov]?.budget_used_pct?.toFixed(0) }}%)
              </span>
            </div>
            <div v-if="billingData[prov]?.actual_sent !== undefined" class="flex justify-between items-center">
              <span class="text-[10px]" style="color: var(--text-muted);">отправлено (БД)</span>
              <span class="text-[10px] font-bold" style="color: var(--text-primary);">{{ billingData[prov]?.actual_sent }}</span>
            </div>
            <div v-if="billingData[prov]?.actual_matches !== undefined" class="flex justify-between items-center">
              <span class="text-[10px]" style="color: var(--text-muted);">совпадений (БД)</span>
              <span class="text-[10px] font-bold" style="color: var(--text-primary);">{{ billingData[prov]?.actual_matches }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card p-4 bg-opacity-5" style="background-color: var(--accent-blue);">
        <h3 class="text-[10px] font-bold uppercase mb-2" style="color: var(--accent-blue);">Заметки</h3>
        <ul class="text-[10px] space-y-1 list-disc list-inside" style="color: var(--text-secondary);">
          <li>Тарифы загружаются из API, можно менять через <code>/api/provider-costs/policies/{provider}</code>.</li>
          <li>Бюджеты и лимиты — <code>/api/provider-costs/budgets/{provider}</code>.</li>
          <li><b>Decodo:</b> расход по трафику (GB), статистика подтягивается автоматически.</li>
          <li><b>SMS:</b> канал заморожен (TCPA). UI показан как beta, расходов нет.</li>
        </ul>
      </div>
    </template>

    <!-- LEAD FUNNEL TAB -->
    <template v-if="activeTab === 'leads'">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="kpi-card">
          <div class="kpi-value">{{ totalLeads }}</div>
          <div class="kpi-label">всего лидов</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value" style="color: var(--accent-red);">{{ priorityCounts.RED || 0 }}</div>
          <div class="kpi-label">высокий приоритет</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value" style="color: var(--accent-yellow);">{{ priorityCounts.YELLOW || 0 }}</div>
          <div class="kpi-label">средний приоритет</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value" style="color: var(--accent-green);">{{ priorityCounts.GREEN || 0 }}</div>
          <div class="kpi-label">низкий приоритет</div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="card p-4">
          <div class="text-[10px] font-semibold tracking-widest uppercase mb-4" style="color: var(--text-secondary);">Лиды по типу кейса</div>
          <div class="space-y-2">
            <div v-for="c in caseData" :key="c.case_type" class="flex items-center gap-2">
              <span class="text-[10px] w-36 truncate" style="color: var(--text-secondary);">{{ c.case_type }}</span>
              <div class="flex-1 h-2" style="background: var(--bg-elevated);">
                <div class="h-full transition-all" :style="{ width: barWidth(c.count, maxCaseCount) + '%', background: caseColor(c.case_type) }"></div>
              </div>
              <span class="text-[10px] w-8 text-right font-semibold" style="color: var(--text-primary);">{{ c.count }}</span>
            </div>
            <div v-if="!caseData.length" class="text-[10px] py-4 text-center" style="color: var(--text-muted);">нет данных по лидам</div>
          </div>
        </div>

        <div class="card p-4">
          <div class="text-[10px] font-semibold tracking-widest uppercase mb-4" style="color: var(--text-secondary);">Воронка по статусу</div>
          <div class="space-y-1">
            <div v-for="(s, idx) in statusFunnel" :key="s.status" class="flex items-center gap-2">
              <span class="text-[10px] w-24" style="color: var(--text-secondary);">{{ s.status }}</span>
              <div class="flex-1 h-3" style="background: var(--bg-elevated);">
                <div class="h-full transition-all" :style="{ width: funnelWidth(s.count) + '%', background: funnelColor(idx) }"></div>
              </div>
              <span class="text-[10px] w-8 text-right font-semibold" style="color: var(--text-primary);">{{ s.count }}</span>
            </div>
            <div v-if="!statusFunnel.length" class="text-[10px] py-4 text-center" style="color: var(--text-muted);">нет данных</div>
          </div>
        </div>
      </div>
    </template>

    <!-- OUTBOUND TAB -->
    <template v-if="activeTab === 'outbound'">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="kpi-card">
          <div class="kpi-value">{{ outbound.letters_sent || 0 }}</div>
          <div class="kpi-label">писем отправлено (Lob)</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">{{ outbound.emails_sent || 0 }}</div>
          <div class="kpi-label">email отправлено (SendGrid)</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">{{ outbound.calls_made || 0 }}</div>
          <div class="kpi-label">звонков совершено</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value" style="color: var(--accent-cyan);">{{ outbound.response_rate || '0%' }}</div>
          <div class="kpi-label">отклик</div>
        </div>
      </div>

      <div class="card p-4">
        <div class="text-[10px] font-semibold tracking-widest uppercase mb-4" style="color: var(--text-secondary);">Исходящие за 30 дней</div>
        <div class="h-40 flex items-end gap-1">
          <div v-for="(day, idx) in outboundTimeline" :key="idx" class="flex-1 flex flex-col items-center gap-1">
            <div class="w-full" :style="{ height: timelineBarHeight(day.count) + 'px', background: 'var(--accent-cyan)' }"></div>
            <span v-if="idx % 7 === 0" class="text-[8px]" style="color: var(--text-muted);">{{ day.label }}</span>
          </div>
          <div v-if="!outboundTimeline.length" class="text-[10px] w-full text-center py-8" style="color: var(--text-muted);">пока нет данных</div>
        </div>
      </div>
    </template>

    <!-- PARSERS TAB -->
    <template v-if="activeTab === 'parsers'">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div v-for="src in parserSources" :key="src.name" class="card p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-[10px] font-semibold tracking-widest uppercase" style="color: var(--text-secondary);">{{ src.name }}</span>
            <span class="badge" :class="src.last_status === 'completed' ? 'badge-green' : src.last_status === 'failed' ? 'badge-red' : 'badge-gray'">
              {{ src.last_status || 'простой' }}
            </span>
          </div>
          <div class="kpi-value mb-1">{{ src.total_records || 0 }}</div>
          <div class="kpi-label">всего записей</div>
          <div class="mt-3 space-y-1">
            <div class="flex justify-between text-[10px]">
              <span style="color: var(--text-muted);">успешность</span>
              <span style="color: var(--text-primary);">{{ src.success_rate || '--' }}</span>
            </div>
            <div class="flex justify-between text-[10px]">
              <span style="color: var(--text-muted);">последний парсинг</span>
              <span style="color: var(--text-primary);">{{ src.last_parse || '--' }}</span>
            </div>
            <div class="flex justify-between text-[10px]">
              <span style="color: var(--text-muted);">всего задач</span>
              <span style="color: var(--text-primary);">{{ src.total_jobs || 0 }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getLeadsByCase, getLeadsByPriority, getLeadsByStatus, getOutboundStats, getOverviewStats, getBillingStats } from '../api'

const tabs = [
  { id: 'leads', label: 'Лиды' },
  { id: 'outbound', label: 'Рассылка' },
  { id: 'parsers', label: 'Парсеры' },
  { id: 'billing', label: 'Биллинг' },
]

const providerOrder = ['batchdata', 'lob', 'sendgrid', 'decodo', 'sms_beta']
const providerLabels = {
  batchdata: 'BatchData',
  lob: 'Lob',
  sendgrid: 'SendGrid',
  decodo: 'Decodo',
  sms_beta: 'SMS',
}

const activeTab = ref('leads')
const caseData = ref([])
const priorityCounts = ref({})
const statusFunnel = ref([])
const outbound = ref({})
const outboundTimeline = ref([])
const parserSources = ref([])
const billingData = ref({})

const totalLeads = computed(() => caseData.value.reduce((s, c) => s + (c.count || 0), 0))
const maxCaseCount = computed(() => Math.max(...caseData.value.map(c => c.count), 1))

function barWidth(count, max) {
  return Math.round(count / max * 100)
}

const CASE_COLORS = {
  PERMIT_SNIPER: 'var(--accent-cyan)',
  EMERGENCY_PLUMBING: 'var(--accent-red)',
  HELOC_NO_PERMIT: 'var(--accent-yellow)',
  NEW_PURCHASE_HELOC: 'var(--accent-green)',
  MECHANICS_LIEN: '#bb88ff',
  ESCROW_FALLOUT: 'var(--accent-blue)',
  ELECTRICAL_REWIRE: '#66ccff',
  STORM_ROOF_DAMAGE: '#ff8844',
}

function caseColor(caseType) {
  return CASE_COLORS[caseType] || 'var(--accent-cyan)'
}

function funnelWidth(count) {
  const max = Math.max(...statusFunnel.value.map(s => s.count), 1)
  return Math.round(count / max * 100)
}

function funnelColor(idx) {
  const colors = ['var(--accent-cyan)', 'var(--accent-blue)', 'var(--accent-yellow)', 'var(--accent-green)', '#bb88ff', 'var(--text-muted)']
  return colors[idx % colors.length]
}

function timelineBarHeight(count) {
  const max = Math.max(...outboundTimeline.value.map(d => d.count), 1)
  return Math.round(count / max * 120)
}

async function loadData() {
  const results = await Promise.allSettled([
    getLeadsByCase(),
    getLeadsByPriority(),
    getLeadsByStatus(),
    getOutboundStats(),
    getOverviewStats(),
    getBillingStats(),
  ])

  if (results[0].status === 'fulfilled') {
    caseData.value = results[0].value.cases || results[0].value || []
  }
  if (results[1].status === 'fulfilled') {
    const d = results[1].value
    priorityCounts.value = d.priorities || d || {}
  }
  if (results[2].status === 'fulfilled') {
    statusFunnel.value = results[2].value.statuses || results[2].value || []
  }
  if (results[3].status === 'fulfilled') {
    const d = results[3].value
    outbound.value = d
    outboundTimeline.value = d.timeline || []
  }
  if (results[5].status === 'fulfilled') {
    billingData.value = results[5].value || {}
  }
  if (results[4].status === 'fulfilled') {
    const stats = results[4].value
    parserSources.value = [
      {
        name: 'SDCI PERMITS',
        total_records: stats.permits?.total_permits || 0,
        success_rate: stats.permits?.success_rate || '--',
        last_parse: stats.permits?.last_parse || '--',
        last_status: stats.permits?.last_status || 'idle',
        total_jobs: stats.permits?.total_jobs || 0,
      },
      {
        name: 'MYBUILDINGPERMIT',
        total_records: stats.mbp?.total_permits || 0,
        success_rate: stats.mbp?.success_rate || '--',
        last_parse: stats.mbp?.last_parse || '--',
        last_status: stats.mbp?.last_status || 'idle',
        total_jobs: stats.mbp?.total_jobs || 0,
      },
      {
        name: 'ZILLOW',
        total_records: stats.zillow?.total_homes || 0,
        success_rate: stats.zillow?.success_rate || '--',
        last_parse: stats.zillow?.last_parse || '--',
        last_status: stats.zillow?.last_status || 'idle',
        total_jobs: stats.zillow?.total_jobs || 0,
      },
    ]
  }
}

onMounted(loadData)
</script>
