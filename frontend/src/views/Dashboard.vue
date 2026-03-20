<template>
  <div class="space-y-4 animate-fadeIn">
    <div class="flex items-center justify-between">
      <div>
        <div class="text-[9px] mb-1" style="color: var(--text-muted);">/операции/журнал</div>
        <h1 class="font-bold tracking-wide" style="color: var(--text-primary);">ОПЕРАЦИИ</h1>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-[9px]" style="color: var(--text-muted);">автообновление 5 с</span>
        <button class="btn-secondary" @click="loadData">Обновить</button>
      </div>
    </div>

    <div class="flex gap-0 border-b" style="border-color: var(--border);">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="terminal-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }} ({{ tabCount(tab.id) }})
      </button>
    </div>

    <div v-if="activeTab === 'archive' || activeTab === 'errors'" class="flex items-center gap-3">
      <select v-model="filterType" class="text-[9px] py-1 px-2">
        <option value="">все типы</option>
        <option value="scheduled">Запланированные</option>
        <option value="permit">Пермит</option>
        <option value="mybuilding">MyBuilding</option>
      </select>
      <input v-model="filterSearch" type="text" placeholder="поиск..." class="text-[9px] py-1 px-2 w-40" />
    </div>

    <div class="card p-0">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr>
              <th class="table-header">статус</th>
              <th class="table-header">парсер</th>
              <th class="table-header">id</th>
              <th class="table-header">{{ activeTab === 'scheduled' ? 'к запуску' : 'начало' }}</th>
              <th class="table-header">{{ activeTab === 'scheduled' ? 'расписание' : 'завершение' }}</th>
              <th class="table-header">длительность</th>
              <th class="table-header">результат</th>
              <th class="table-header w-36"></th>
            </tr>
          </thead>
          <tbody v-if="!filteredJobs.length">
            <tr>
              <td class="table-cell text-center" colspan="8" style="color: var(--text-muted); padding: 20px;">
                {{ activeTab === 'scheduled' ? 'Нет запланированных операций' : activeTab === 'active' ? 'Нет активных операций' : activeTab === 'errors' ? 'Нет ошибок' : 'Архив пуст' }}
              </td>
            </tr>
          </tbody>
          <tbody v-for="job in filteredJobs" :key="job.id">
            <tr class="hover:bg-[var(--bg-base)]">
              <td class="table-cell">
                <span class="badge" :class="statusBadge(job.status)">{{ statusRu(job.status) }}</span>
              </td>
              <td class="table-cell" style="color: var(--text-primary);">{{ job.parser_name }}</td>
              <td class="table-cell" style="color: var(--text-muted);">#{{ job.id }}</td>
              <td class="table-cell" style="color: var(--text-secondary);">
                <template v-if="isScheduledJob(job)">
                  <div>{{ formatDT(job.scheduled_at) }}</div>
                  <div class="text-[8px]" style="color: var(--text-muted);">{{ relativeTime(job.scheduled_at) }}</div>
                </template>
                <template v-else>{{ formatDT(job.started_at) }}</template>
              </td>
              <td class="table-cell" style="color: var(--text-secondary);">
                <template v-if="isScheduledJob(job)">
                  <span v-if="job.is_recurring" class="text-[9px]">каждые {{ job.recurrence_interval_days || 2 }} дн.</span>
                  <span v-else class="text-[9px]">однократно</span>
                </template>
                <template v-else>{{ formatDT(job.finished_at) }}</template>
              </td>
              <td class="table-cell" style="color: var(--text-secondary);">{{ isScheduledJob(job) ? '—' : (job.duration || '—') }}</td>
              <td class="table-cell" style="color: var(--text-secondary);">{{ job.result_summary || '—' }}</td>
              <td class="table-cell">
                <div class="flex items-center gap-1.5">
                  <button type="button" class="btn-secondary text-[9px] py-0.5 px-2" @click="openDetail(job)">Детали парсера</button>
                  <button v-if="isScheduledJob(job)" type="button" class="btn-danger text-[9px] py-0.5 px-2" @click="cancelScheduled(job)">Отменить</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="detailJob"
        class="fixed inset-0 z-[100] flex items-center justify-center p-4"
        style="background: rgba(0,0,0,0.6);"
        @click.self="closeDetail"
      >
        <div
          class="card max-w-2xl w-full max-h-[85vh] overflow-y-auto p-4 border"
          style="border-color: var(--border-active); background: var(--bg-surface);"
          role="dialog"
          aria-labelledby="parser-detail-title"
          @click.stop
        >
          <div class="flex items-start justify-between gap-3 mb-3">
            <div>
              <div id="parser-detail-title" class="text-[10px] uppercase font-semibold tracking-wide" style="color: var(--text-muted);">Детали парсера</div>
              <div class="text-[13px] font-semibold mt-1" style="color: var(--text-primary);">
                {{ detailJob.parser_name }} · #{{ detailJob.id }}
                <span v-if="isScheduledJob(detailJob)" class="ml-2 text-[10px]" style="color: var(--text-muted);">запланированная операция</span>
              </div>
              <div v-if="isScheduledJob(detailJob)" class="text-[10px] mt-1" style="color: var(--text-muted);">
                Запуск: {{ formatDT(detailJob.scheduled_at) }} ({{ relativeTime(detailJob.scheduled_at) }})
                <span v-if="detailJob.is_recurring"> · повтор каждые {{ detailJob.recurrence_interval_days || 2 }} дн.</span>
              </div>
            </div>
            <button type="button" class="btn-secondary text-[9px] py-1 px-2 shrink-0" @click="closeDetail">Закрыть</button>
          </div>

          <section class="mb-4">
            <h3 class="text-[10px] uppercase font-semibold mb-2" style="color: var(--text-secondary);">Каналы</h3>
            <ParserChannelToolbar
              :model-value="editChannels"
              :editable="canEditChannels"
              :saving="channelSaving"
              :hint="channelsToolbarHint"
              @update:model-value="onChannelsToolbarUpdate"
            />
            <div v-if="canEditChannels" class="flex items-center gap-2 mt-3">
              <button type="button" class="btn-primary text-[9px] py-1 px-2" :disabled="channelSaving" @click="saveChannels">
                {{ channelSaving ? 'Сохранение...' : 'Сохранить каналы' }}
              </button>
              <span v-if="channelMessage" class="text-[9px]" style="color: var(--text-muted);">{{ channelMessage }}</span>
            </div>
          </section>

          <section class="mb-4">
            <h3 class="text-[10px] uppercase font-semibold mb-2" style="color: var(--text-secondary);">Параметры парсера</h3>
            <div v-if="detailCfgRows.length" class="space-y-1.5 text-[11px]">
              <div v-for="([label, val], i) in detailCfgRows" :key="'cfg-' + i" class="grid grid-cols-[minmax(0,220px)_1fr] gap-x-3">
                <span style="color: var(--text-muted);">{{ label }}</span>
                <span style="color: var(--text-primary);">{{ val }}</span>
              </div>
            </div>
            <p v-else class="text-[10px]" style="color: var(--text-muted);">—</p>
          </section>

          <section v-if="detailFixedRows.length" class="mb-4">
            <h3 class="text-[10px] uppercase font-semibold mb-2" style="color: var(--text-secondary);">Фиксированные настройки</h3>
            <div class="space-y-1.5 text-[11px]">
              <div v-for="([label, val], i) in detailFixedRows" :key="'fixed-' + i" class="grid grid-cols-[minmax(0,220px)_1fr] gap-x-3">
                <span style="color: var(--text-muted);">{{ label }}</span>
                <span style="color: var(--text-primary);">{{ val }}</span>
              </div>
            </div>
          </section>

          <section v-if="detailResRows.length" class="mb-4">
            <h3 class="text-[10px] uppercase font-semibold mb-2" style="color: var(--text-secondary);">Результат</h3>
            <div class="space-y-1.5 text-[11px]">
              <div v-for="([label, val], i) in detailResRows" :key="'res-' + i" class="grid grid-cols-[minmax(0,220px)_1fr] gap-x-3">
                <span style="color: var(--text-muted);">{{ label }}</span>
                <span style="color: var(--text-primary);">{{ val }}</span>
              </div>
            </div>
          </section>

          <div class="pt-2 border-t" style="border-color: var(--border);">
            <button type="button" class="btn-primary text-[10px] py-1.5 px-3" :disabled="applyLoading" @click="applyToNextParsers">
              {{ applyLoading ? 'Применение...' : 'Применить к следующим парсерам' }}
            </button>
            <p v-if="applyMessage" class="text-[10px] mt-2" style="color: var(--text-muted);">{{ applyMessage }}</p>
          </div>

          <div v-if="detailJob.error" class="p-2 rounded text-[10px] mt-3" style="background: var(--bg-base); border: 1px solid rgba(248,113,113,0.35); color: #b91c1c;">{{ detailJob.error }}</div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import ParserChannelToolbar from '../components/ParserChannelToolbar.vue'
import { applyParserSettingsToNextJobs, cancelScheduledOperation, getJobDetail, getJobsList, updateScheduledOperation } from '../api'

const jobs = ref([])
const activeTab = ref('active')
const filterType = ref('')
const filterSearch = ref('')
const detailJob = ref(null)
const applyLoading = ref(false)
const applyMessage = ref('')
const channelSaving = ref(false)
const channelMessage = ref('')
const editChannels = reactive({ physical_mail: false, email: false, enrichment: false })
let pollTimer = null

const tabs = [
  { id: 'scheduled', label: 'запланированные' },
  { id: 'active', label: 'активные' },
  { id: 'archive', label: 'архив' },
  { id: 'errors', label: 'ошибки' },
]

const ACTIVE_STATUSES = ['running', 'parsing', 'verifying', 'pending', 'queued']
const ARCHIVE_STATUSES = ['completed', 'cancelled', 'skipped']

function parserKind(job) {
  if (job?.is_scheduled_operation) return 'scheduled'
  if (job?.operation_type === 'permit') return 'permit'
  if (job?.operation_type === 'mybuilding') return 'mybuilding'
  const t = String(job?.type || '').toLowerCase()
  if (t === 'permits' || t.includes('sdci') || t.includes('permit')) return 'permit'
  if (t === 'mbp' || t.includes('mybuilding')) return 'mybuilding'
  return null
}

const STATUS_RU = {
  scheduled: 'Запланировано',
  dispatching: 'Отправка',
  running: 'Выполняется',
  parsing: 'Парсинг',
  verifying: 'Проверка',
  pending: 'Ожидание',
  queued: 'В очереди',
  completed: 'Завершено',
  failed: 'Ошибка',
  cancelled: 'Отменено',
  skipped: 'Пропущено',
}

function statusRu(s) {
  return STATUS_RU[s] || s
}

function statusBadge(status) {
  const map = {
    scheduled: 'badge-gray',
    dispatching: 'badge-blue',
    running: 'badge-blue',
    parsing: 'badge-blue',
    verifying: 'badge-blue',
    pending: 'badge-gray',
    queued: 'badge-gray',
    completed: 'badge-green',
    failed: 'badge-red',
    cancelled: 'badge-gray',
    skipped: 'badge-gray',
  }
  return map[status] || 'badge-gray'
}

const dtFmt = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: 'America/Los_Angeles',
})

function formatDT(dateStr) {
  if (!dateStr) return '—'
  return dtFmt.format(new Date(dateStr)) + ' PST'
}

function relativeTime(dateStr) {
  if (!dateStr) return ''
  const diff = new Date(dateStr) - Date.now()
  if (diff < 0) return 'просрочено'
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `через ${mins} мин.`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `через ${hours} ч. ${mins % 60} мин.`
  const days = Math.floor(hours / 24)
  return `через ${days} дн. ${hours % 24} ч.`
}

const visibleJobs = computed(() => jobs.value.filter((j) => parserKind(j)))

function tabCount(tabId) {
  const list = visibleJobs.value
  if (tabId === 'scheduled') return list.filter((j) => ['scheduled', 'dispatching'].includes(j.status) && isScheduledJob(j)).length
  if (tabId === 'active') return list.filter((j) => ACTIVE_STATUSES.includes(j.status)).length
  if (tabId === 'errors') return list.filter((j) => j.status === 'failed').length
  return list.filter((j) => ARCHIVE_STATUSES.includes(j.status)).length
}

const filteredJobs = computed(() => {
  let list = visibleJobs.value
  if (activeTab.value === 'scheduled') list = list.filter((j) => ['scheduled', 'dispatching'].includes(j.status) && isScheduledJob(j))
  if (activeTab.value === 'active') list = list.filter((j) => ACTIVE_STATUSES.includes(j.status))
  if (activeTab.value === 'errors') list = list.filter((j) => j.status === 'failed')
  if (activeTab.value === 'archive') list = list.filter((j) => ARCHIVE_STATUSES.includes(j.status))

  if (filterType.value) list = list.filter((j) => parserKind(j) === filterType.value)

  if (filterSearch.value) {
    const q = filterSearch.value.toLowerCase()
    list = list.filter((j) => {
      const parserName = String(j.parser_name || '').toLowerCase()
      const type = String(j.type || '').toLowerCase()
      return parserName.includes(q) || type.includes(q) || String(j.id).includes(q)
    })
  }
  return list
})

/** Редактирование каналов API — только запланированная операция со статусом «scheduled». */
const canEditChannels = computed(() => {
  const j = detailJob.value
  if (!j || !isScheduledJob(j)) return false
  return j.status === 'scheduled'
})

const channelsToolbarHint = computed(() => {
  if (!detailJob.value) return ''
  if (canEditChannels.value) return 'Нажмите на канал, чтобы включить или выключить, затем «Сохранить каналы».'
  if (isScheduledJob(detailJob.value) && detailJob.value.status === 'dispatching')
    return 'Операция уже отправляется в работу — каналы только для просмотра.'
  return 'Для активных и завершённых операций каналы только для просмотра.'
})

function syncChannelsFromJob(job) {
  if (!job) return
  Object.assign(editChannels, {
    physical_mail: Boolean(job.channels?.physical_mail),
    email: Boolean(job.channels?.email),
    enrichment: Boolean(job.channels?.enrichment),
  })
}

function onChannelsToolbarUpdate(next) {
  Object.assign(editChannels, next)
}

const detailCfgRows = computed(() => {
  const cfg = detailJob.value?.config || {}
  return Object.entries(cfg).map(([k, v]) => [k, formatAny(v)])
})

const detailFixedRows = computed(() => {
  const fixed = detailJob.value?.fixed_settings || {}
  return Object.entries(fixed).map(([k, v]) => [k, formatAny(v)])
})

const detailResRows = computed(() => {
  const res = detailJob.value?.result || {}
  return Object.entries(res).map(([k, v]) => [k, formatAny(v)])
})

function formatAny(value) {
  if (Array.isArray(value)) return value.join(', ')
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Да' : 'Нет'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function isScheduledJob(job) {
  return Boolean(job?.is_scheduled_operation || job?.operation_type || job?.status === 'scheduled')
}

async function openDetail(job) {
  applyMessage.value = ''
  channelMessage.value = ''
  if (isScheduledJob(job)) {
    detailJob.value = job
    syncChannelsFromJob(job)
    return
  }
  try {
    const full = await getJobDetail(job.id, parserKind(job))
    detailJob.value = {
      ...job,
      ...full,
      parser_name: full.parser_name || job.parser_name,
    }
    syncChannelsFromJob(detailJob.value)
  } catch (error) {
    console.error('Job detail error:', error)
    detailJob.value = job
    syncChannelsFromJob(detailJob.value)
  }
}

function closeDetail() {
  detailJob.value = null
  applyMessage.value = ''
  channelMessage.value = ''
}

async function saveChannels() {
  if (!detailJob.value) return
  channelSaving.value = true
  channelMessage.value = ''
  try {
    await updateScheduledOperation(detailJob.value.id, { channels: { ...editChannels } })
    detailJob.value = { ...detailJob.value, channels: { ...editChannels } }
    channelMessage.value = 'Каналы сохранены'
    await loadData()
  } catch (error) {
    channelMessage.value = error.message || 'Ошибка сохранения'
  } finally {
    channelSaving.value = false
  }
}

async function applyToNextParsers() {
  if (!detailJob.value) return
  applyLoading.value = true
  applyMessage.value = ''
  try {
    let parserType = parserKind(detailJob.value)
    if (parserType === 'scheduled') {
      parserType = detailJob.value.operation_type || null
    }
    if (!parserType || parserType === 'scheduled') {
      throw new Error('Не удалось определить тип парсера для применения настроек')
    }
    const channels = isScheduledJob(detailJob.value) ? { ...editChannels } : (detailJob.value.channels || {})
    const resp = await applyParserSettingsToNextJobs({
      parser_type: parserType,
      channels,
    })
    applyMessage.value = `Обновлено задач в очереди: ${resp.updated_jobs ?? 0}`
    await loadData()
  } catch (error) {
    applyMessage.value = error.message || 'Не удалось применить настройки'
  } finally {
    applyLoading.value = false
  }
}

async function cancelScheduled(job) {
  try {
    await cancelScheduledOperation(job.id, { reason: 'Отменено из /операции' })
    await loadData()
  } catch (error) {
    console.error('Cancel scheduled operation error:', error)
  }
}

async function loadData() {
  try {
    const data = await getJobsList({ limit: 100 })
    const raw = data.jobs || data || []
    jobs.value = raw.map((j) => {
      const kind = parserKind(j)
      let parserName = j.parser_name
      if (!parserName && kind === 'permit') parserName = 'Пермит'
      if (!parserName && kind === 'mybuilding') parserName = 'MyBuilding'
      return { ...j, parser_name: parserName || j.type }
    })
  } catch (e) {
    console.error('Operations load error:', e)
  }
}

onMounted(() => {
  loadData()
  pollTimer = setInterval(loadData, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
