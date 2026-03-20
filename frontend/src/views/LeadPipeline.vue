<template>
  <div class="space-y-4 animate-fadeIn">
    <div class="flex items-center justify-between flex-wrap gap-2">
      <div>
        <div class="text-[10px] mb-1" style="color: var(--text-muted);">/лиды/воронка</div>
        <h1 class="text-xl font-bold tracking-wide" style="color: var(--text-primary);">ЛИДЫ</h1>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-[10px]" style="color: var(--text-muted);">всего: {{ leads.length }}</span>
        <button class="btn-secondary py-1 px-3 text-[10px]" @click="runTelegramTest">Тест Telegram</button>
        <div class="flex gap-0 border" style="border-color: var(--border);">
          <button
            class="py-1 px-3 text-[10px] transition-colors"
            :style="viewMode === 'table' ? { background: 'var(--accent-cyan)', color: 'var(--bg-base)' } : { background: 'transparent', color: 'var(--text-secondary)' }"
            @click="viewMode = 'table'"
          >ТАБЛИЦА</button>
          <button
            class="py-1 px-3 text-[10px] transition-colors border-l"
            style="border-color: var(--border);"
            :style="viewMode === 'kanban' ? { background: 'var(--accent-cyan)', color: 'var(--bg-base)' } : { background: 'transparent', color: 'var(--text-secondary)' }"
            @click="viewMode = 'kanban'"
          >КАНБАН</button>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex items-center gap-2 flex-wrap py-2 px-3 border" style="border-color: var(--border); background: var(--bg-surface);">
      <input v-model="filters.search" type="text" placeholder="поиск..." class="py-1 px-2 w-36 text-[10px]" @keyup.enter="loadLeads" />
      <span class="text-[10px]" style="color: var(--text-muted);">|</span>
      <select v-model="filters.priority" class="py-1 px-2 text-[10px]">
        <option value="">приоритет: все</option>
        <option value="RED">Высокий</option>
        <option value="YELLOW">Средний</option>
        <option value="GREEN">Низкий</option>
      </select>
      <select v-model="filters.caseType" class="py-1 px-2 text-[10px]">
        <option value="">кейс: все</option>
        <option v-for="ct in caseTypes" :key="ct" :value="ct">{{ ct }}</option>
      </select>
      <select v-model="filters.status" class="py-1 px-2 text-[10px]">
        <option value="">статус: все</option>
        <option v-for="s in statuses" :key="s" :value="s">{{ statusLabel(s) }}</option>
      </select>
      <span class="text-[10px]" style="color: var(--text-muted);">|</span>
      <button class="btn-primary py-1 px-3" @click="loadLeads">Применить</button>
    </div>

    <!-- Table View -->
    <div v-if="viewMode === 'table'" class="card p-0">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr>
              <th class="table-header">адрес</th>
              <th class="table-header">кейс</th>
              <th class="table-header">приоритет</th>
              <th class="table-header">статус</th>
              <th class="table-header">источник</th>
              <th class="table-header">контакт</th>
              <th class="table-header">найден</th>
              <th class="table-header">действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!leads.length">
              <td class="table-cell text-center" colspan="8" style="color: var(--text-muted); padding: 24px;">нет лидов</td>
            </tr>
            <tr v-for="lead in leads" :key="lead.id" class="hover-row">
              <td class="table-cell" style="max-width: 200px; color: var(--text-primary);">{{ lead.address }}</td>
              <td class="table-cell"><span class="badge badge-case">{{ lead.case_type }}</span></td>
              <td class="table-cell">
                <span class="badge" :class="priBadge(lead.priority)">{{ lead.priority }}</span>
              </td>
              <td class="table-cell" style="color: var(--text-secondary);">{{ statusLabel(lead.status) }}</td>
              <td class="table-cell" style="color: var(--text-muted);">{{ lead.source || '-' }}</td>
              <td class="table-cell" style="color: var(--text-secondary);">{{ lead.contact_name || '-' }}</td>
              <td class="table-cell" style="color: var(--text-muted);">{{ fmtDate(lead.found_at) }}</td>
              <td class="table-cell">
                <div class="flex items-center gap-1">
                  <template v-if="lead.status === 'pending_review'">
                    <button class="btn-primary py-0.5 px-2 text-[9px]" @click="approve(lead.id)">Одобрить</button>
                  </template>
                  <!-- Call action: click opens traffic-light menu -->
                  <div class="relative inline-block">
                    <button
                      class="action-btn py-1 px-2 text-[10px] border"
                      style="border-color: var(--border); color: var(--text-secondary); min-width: 28px;"
                      title="Исход звонка"
                      @click.stop="callMenuLeadId === lead.id ? (callMenuLeadId = null) : (callMenuLeadId = lead.id)"
                    >
                      &#9742;
                    </button>
                    <div
                      v-if="callMenuLeadId === lead.id"
                      class="absolute left-0 top-full mt-1 z-20 flex flex-col border p-1 gap-0"
                      style="background: var(--bg-elevated); border-color: var(--border); min-width: 140px;"
                      @click.stop
                    >
                      <button class="call-outcome-btn text-left py-1.5 px-2 text-[10px] flex items-center gap-2" style="color: var(--accent-green);" @click="setCallOutcome(lead.id, 'contacted')">
                        <span aria-hidden="true">&#10003;</span> Связались
                      </button>
                      <button class="call-outcome-btn text-left py-1.5 px-2 text-[10px] flex items-center gap-2" style="color: var(--accent-yellow);" @click="setCallOutcome(lead.id, 'no_answer')">
                        <span aria-hidden="true">&#8634;</span> Не ответил
                      </button>
                      <button class="call-outcome-btn text-left py-1.5 px-2 text-[10px] flex items-center gap-2" style="color: var(--accent-red);" @click="setCallOutcome(lead.id, 'closed')">
                        <span aria-hidden="true">&#215;</span> В архив
                      </button>
                      <button class="call-outcome-btn text-left py-1.5 px-2 text-[10px] flex items-center gap-2" style="color: var(--text-secondary);" @click="snoozeLeadCall(lead.id)">
                        <span aria-hidden="true">&#8986;</span> +1 день
                      </button>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Kanban View -->
    <div v-else class="grid grid-cols-1 md:grid-cols-4 gap-3">
      <div
        v-for="col in kanbanColumns"
        :key="col.status"
        class="kanban-col border p-3 flex flex-col"
        style="background: var(--bg-surface); border-color: var(--border); min-height: 320px;"
        @dragover.prevent="dragOverCol = col.status"
        @dragleave="dragOverCol = null"
        @drop.prevent="onDrop(col.status)"
        :style="{ outline: dragOverCol === col.status ? '2px solid var(--accent-cyan)' : 'none' }"
      >
        <div class="text-[10px] font-semibold uppercase mb-2" :style="{ color: col.color }">{{ col.label }}</div>
        <div class="flex-1 space-y-2 overflow-y-auto">
          <div
            v-for="lead in kanbanLeads(col.status)"
            :key="lead.id"
            class="kanban-card p-2 border cursor-grab transition-colors"
            style="background: var(--bg-elevated); border-color: var(--border);"
            draggable="true"
            @dragstart="onDragStart($event, lead)"
            @dragend="dragLeadId = null"
          >
            <div class="text-[10px] truncate font-medium" style="color: var(--text-primary);">{{ lead.address }}</div>
            <div class="flex items-center gap-1 mt-1">
              <span class="badge text-[8px]" :class="priBadge(lead.priority)">{{ lead.priority }}</span>
              <span class="badge badge-case text-[8px]">{{ lead.case_type }}</span>
            </div>
            <div class="mt-2 flex gap-1">
              <template v-if="lead.status === 'pending_review'">
                <button class="btn-primary py-0.5 px-1.5 text-[8px]" @click="approve(lead.id)">Одобрить</button>
              </template>
              <div class="relative">
                <button class="py-0.5 px-1.5 text-[8px] border" style="border-color: var(--border); color: var(--text-secondary);" title="Исход звонка" @click.stop="callMenuLeadId === lead.id ? (callMenuLeadId = null) : (callMenuLeadId = lead.id)">&#9742;</button>
                <div v-if="callMenuLeadId === lead.id" class="absolute left-0 top-full mt-1 z-20 flex flex-col border p-1 gap-0" style="background: var(--bg-base); border-color: var(--border); min-width: 120px;" @click.stop>
                  <button class="text-left py-1 px-2 text-[9px]" style="color: var(--accent-green);" @click="setCallOutcome(lead.id, 'contacted')">Связались</button>
                  <button class="text-left py-1 px-2 text-[9px]" style="color: var(--accent-yellow);" @click="setCallOutcome(lead.id, 'no_answer')">Не ответил</button>
                  <button class="text-left py-1 px-2 text-[9px]" style="color: var(--accent-red);" @click="setCallOutcome(lead.id, 'closed')">В архив</button>
                  <button class="text-left py-1 px-2 text-[9px]" style="color: var(--text-secondary);" @click="snoozeLeadCall(lead.id)">+1 день</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Click outside to close call menu -->
    <div v-if="callMenuLeadId" class="fixed inset-0 z-10" @click="callMenuLeadId = null" aria-hidden="true"></div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import { getLeads, approveLead, updateLeadStatus, snoozeTask, sendTelegramTest } from '../api'

const leads = ref([])
const filters = reactive({ search: '', priority: '', caseType: '', status: '' })
const viewMode = ref('table')
const callMenuLeadId = ref(null)
const dragLeadId = ref(null)
const dragOverCol = ref(null)

const caseTypes = ['PERMIT_SNIPER', 'EMERGENCY_PLUMBING', 'HELOC_NO_PERMIT', 'NEW_PURCHASE_HELOC', 'MECHANICS_LIEN', 'ESCROW_FALLOUT', 'ELECTRICAL_REWIRE', 'STORM_ROOF_DAMAGE']
const statuses = ['new', 'pending_review', 'approved', 'letter_sent', 'email_sent', 'contacted', 'no_answer', 'closed']

const kanbanColumns = [
  { status: 'to_call', label: 'Позвонить', color: 'var(--accent-cyan)' },
  { status: 'contacted', label: 'Связались', color: 'var(--accent-green)' },
  { status: 'no_answer', label: 'Не ответил', color: 'var(--accent-yellow)' },
  { status: 'closed', label: 'Архив', color: 'var(--text-muted)' },
]

function kanbanLeads(colStatus) {
  if (colStatus === 'to_call') {
    return leads.value.filter(l => !['contacted', 'no_answer', 'closed'].includes(l.status))
  }
  return leads.value.filter(l => l.status === colStatus)
}

function openCallMenu(leadId) {
  return callMenuLeadId.value
}

const statusLabels = {
  new: 'Новый',
  pending_review: 'На проверке',
  approved: 'Одобрен',
  letter_sent: 'Письмо отправлено',
  email_sent: 'Email отправлен',
  contacted: 'Связались',
  no_answer: 'Не ответил',
  closed: 'Архив',
}
function statusLabel(s) {
  return statusLabels[s] || s
}

function priBadge(p) {
  if (p === 'RED') return 'badge-red'
  if (p === 'YELLOW') return 'badge-yellow'
  return 'badge-green'
}

function fmtDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

async function loadLeads() {
  const res = await getLeads({ search: filters.search, priority: filters.priority, case_type: filters.caseType, status: filters.status })
  leads.value = res.leads || res || []
}

async function approve(id) {
  await approveLead(id, 'admin', 'Approved')
  callMenuLeadId.value = null
  await loadLeads()
}

async function setCallOutcome(leadId, status) {
  await updateLeadStatus(leadId, status)
  callMenuLeadId.value = null
  await loadLeads()
}

async function snoozeLeadCall(leadId) {
  await snoozeTask(leadId, 24)
  callMenuLeadId.value = null
  await loadLeads()
}

async function runTelegramTest() {
  await sendTelegramTest()
}

function onDragStart(e, lead) {
  dragLeadId.value = lead.id
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', lead.id)
  e.dataTransfer.setData('application/json', JSON.stringify({ id: lead.id }))
}

async function onDrop(targetStatus) {
  const id = dragLeadId.value
  dragOverCol.value = null
  dragLeadId.value = null
  if (!id) return
  const lead = leads.value.find(l => l.id === id)
  if (!lead) return
  if (targetStatus === 'to_call') {
    if (['contacted', 'no_answer', 'closed'].includes(lead.status)) {
      await updateLeadStatus(id, 'new')
      await loadLeads()
    }
  } else {
    await updateLeadStatus(id, targetStatus)
    await loadLeads()
  }
}

onMounted(loadLeads)
</script>

<style scoped>
.hover-row:hover { background: var(--bg-elevated); }
.call-outcome-btn:hover { background: var(--bg-base); }
.kanban-card:active { cursor: grabbing; }
</style>
