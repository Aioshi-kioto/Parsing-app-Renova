<template>
  <div class="space-y-5 animate-fadeIn">
    <div>
      <div class="text-[10px] mb-1" style="color: var(--text-muted);">/парсеры/permits</div>
      <h1 class="text-lg font-semibold" style="color: var(--text-primary);">Настройки парсера Seattle Permits</h1>
      <p class="text-[11px] mt-1" style="color: var(--text-secondary);">
        Эта страница только для конфигурации. Ручной запуск отключен.
      </p>
    </div>

    <div class="card p-4 space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label class="block text-[11px] mb-1" style="color: var(--text-muted);">Год</label>
          <input v-model.number="config.year" type="number" class="w-full px-2 py-1.5 border rounded" style="border-color: var(--border);" />
        </div>
        <div>
          <label class="block text-[11px] mb-1" style="color: var(--text-muted);">Месяц</label>
          <select v-model="config.month" class="w-full px-2 py-1.5 border rounded" style="border-color: var(--border);">
            <option :value="null">Все</option>
            <option v-for="m in 12" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <div>
          <label class="block text-[11px] mb-1" style="color: var(--text-muted);">Класс пермита</label>
          <input v-model="config.permit_class" type="text" class="w-full px-2 py-1.5 border rounded" style="border-color: var(--border);" />
        </div>
        <div>
          <label class="block text-[11px] mb-1" style="color: var(--text-muted);">Мин. стоимость ($)</label>
          <input v-model.number="config.min_cost" type="number" min="0" class="w-full px-2 py-1.5 border rounded" style="border-color: var(--border);" />
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <label class="flex items-center gap-2 text-[11px]" style="color: var(--text-secondary);">
          <input v-model="config.browser_visible" type="checkbox" />
          Показывать браузер при верификации
        </label>
        <label class="flex items-center gap-2 text-[11px]" style="color: var(--text-secondary);">
          <input type="checkbox" checked disabled />
          Проверять Owner-Builder (фиксировано для Seattle)
        </label>
      </div>

      <div>
        <div class="text-[11px] mb-2" style="color: var(--text-muted);">Каналы (для новых задач)</div>
        <div class="flex flex-wrap gap-4 text-[11px]" style="color: var(--text-secondary);">
          <label class="flex items-center gap-2">
            <input v-model="channels.physical_mail" type="checkbox" />
            Физическая рассылка (Lob)
          </label>
          <label class="flex items-center gap-2">
            <input v-model="channels.email" type="checkbox" />
            Электронная рассылка (SendGrid)
          </label>
          <label class="flex items-center gap-2">
            <input v-model="channels.enrichment" type="checkbox" />
            Обогащение контактов (BatchData)
          </label>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <button class="btn-primary text-[11px] px-3 py-1.5" :disabled="saving" @click="saveSettings">
          {{ saving ? 'Применение...' : 'Применить' }}
        </button>
        <span v-if="message" class="text-[11px]" style="color: var(--text-muted);">{{ message }}</span>
      </div>

      <div class="pt-3 border-t space-y-2" style="border-color: var(--border);">
        <div class="text-[11px]" style="color: var(--text-muted);">Планирование запуска</div>
        <div class="flex items-end gap-3 flex-wrap">
          <div>
            <label class="block text-[11px] mb-1" style="color: var(--text-muted);">Дата и время (локально)</label>
            <input v-model="scheduleAtLocal" type="datetime-local" class="px-2 py-1.5 border rounded" style="border-color: var(--border);" />
          </div>
          <button class="btn-secondary text-[11px] px-3 py-1.5" :disabled="saving || !scheduleAtLocal" @click="scheduleOperation">
            Запланировать
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { applyParserSettingsToNextJobs, createScheduledOperation, getParserSettings, updateParserSettings } from '../api'

const config = reactive({
  year: new Date().getFullYear(),
  month: null,
  permit_class: 'Single Family / Duplex',
  min_cost: 5000,
  verify_owner_builder: true,
  browser_visible: true,
})

const channels = reactive({
  physical_mail: true,
  email: true,
  enrichment: true,
})

const saving = ref(false)
const message = ref('')
const scheduleAtLocal = ref('')

async function loadSettings() {
  const data = await getParserSettings('permit')
  Object.assign(config, data.config || {})
  Object.assign(channels, data.channels || {})
}

async function saveSettings() {
  saving.value = true
  message.value = ''
  try {
    await updateParserSettings('permit', {
      config: {
        ...config,
        verify_owner_builder: true,
      },
      channels: { ...channels },
    })
    const result = await applyParserSettingsToNextJobs({
      parser_type: 'permit',
      config: {
        ...config,
        verify_owner_builder: true,
      },
      channels: { ...channels },
    })
    message.value = `Настройки сохранены. Обновлено задач в очереди: ${result.updated_jobs ?? 0}`
  } catch (error) {
    message.value = error.message || 'Не удалось сохранить настройки'
  } finally {
    saving.value = false
  }
}

function localToUtcIso(localValue) {
  const dt = new Date(localValue)
  if (Number.isNaN(dt.getTime())) return null
  return dt.toISOString()
}

async function scheduleOperation() {
  if (!scheduleAtLocal.value) return
  saving.value = true
  message.value = ''
  try {
    const runAtUtc = localToUtcIso(scheduleAtLocal.value)
    if (!runAtUtc) {
      throw new Error('Некорректная дата/время')
    }

    await createScheduledOperation({
      operation_type: 'permit',
      run_at_utc: runAtUtc,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      payload: {
        ...config,
        verify_owner_builder: true,
      },
      channels: { ...channels },
      fixed_settings: {
        source: 'Seattle SDCI',
        check_owner_builder_always: true,
      },
    })
    message.value = 'Будущая операция успешно запланирована'
  } catch (error) {
    message.value = error.message || 'Не удалось запланировать операцию'
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>
