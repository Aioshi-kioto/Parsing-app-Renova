<template>
  <div class="ops-expand-panel px-3 py-3 space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <span class="text-[10px] uppercase font-semibold tracking-wide" style="color: var(--text-secondary);">Подпроцессы</span>
      <button type="button" class="btn-secondary text-[9px] py-0.5 px-2" @click="$emit('open-detail')">Детали парсера</button>
    </div>

    <div class="rounded border overflow-hidden" style="border-color: var(--border); background: var(--bg-base);">
      <table class="w-full">
        <thead>
          <tr style="background: var(--bg-surface);">
            <th class="table-header">статус</th>
            <th class="table-header">этап</th>
            <th class="table-header">начало</th>
            <th class="table-header">завершение</th>
            <th class="table-header">результат</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!subs.length">
            <td class="table-cell text-center" colspan="5" style="color: var(--text-muted);">Нет подпроцессов</td>
          </tr>
          <tr v-for="sp in subs" :key="sp.id" class="border-t" style="border-color: var(--border);">
            <td class="table-cell">
              <span class="badge" :class="statusBadge(sp.status)">{{ statusRu(sp.status) }}</span>
            </td>
            <td class="table-cell font-medium" style="color: var(--text-primary);">{{ sp.title }}</td>
            <td class="table-cell" style="color: var(--text-secondary);">{{ formatDT(sp.started_at) }}</td>
            <td class="table-cell" style="color: var(--text-secondary);">{{ formatDT(sp.completed_at) }}</td>
            <td class="table-cell" style="color: var(--text-secondary);">
              <template v-if="sp.counts">{{ sp.counts.processed }}/{{ sp.counts.total }} — {{ sp.result || '—' }}</template>
              <template v-else>{{ sp.result || '—' }}</template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="job.error"
      class="rounded p-2.5 text-[10px] leading-relaxed"
      style="background: #1a0f0f; border: 1px solid rgba(248,113,113,0.4); color: #fecaca;"
    >
      {{ job.error }}
    </div>

    <div
      v-if="job.log"
      class="rounded p-2.5 text-[9px] leading-relaxed font-mono max-h-[120px] overflow-y-auto"
      style="background: #0c1210; border: 1px solid var(--border); color: #86efac;"
    >
      {{ job.log }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  job: { type: Object, required: true },
  formatDT: { type: Function, required: true },
  statusRu: { type: Function, required: true },
  statusBadge: { type: Function, required: true },
})

defineEmits(['open-detail'])

const subs = computed(() => props.job.subprocesses || [])
</script>

<style scoped>
.ops-expand-panel {
  background: var(--bg-surface);
}
</style>
