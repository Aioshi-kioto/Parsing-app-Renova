<template>
  <div class="space-y-5 animate-fadeIn">
    <div>
      <div class="text-[10px] mb-1" style="color: var(--text-muted);">/парсеры/mybuildingpermit</div>
      <h1 class="text-lg font-semibold" style="color: var(--text-primary);">Настройки парсера MyBuildingPermit</h1>
      <p class="text-[11px] mt-1" style="color: var(--text-secondary);">
        Эта страница только для конфигурации. Ручной запуск отключен.
      </p>
    </div>

    <div class="card p-4 space-y-4">
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="text-[11px]" style="color: var(--text-muted);">Юрисдикции</label>
          <div class="flex gap-2">
            <button type="button" class="btn-secondary text-[10px] px-2 py-1" @click="selectAll">Выбрать все</button>
            <button type="button" class="btn-secondary text-[10px] px-2 py-1" @click="clearAll">Очистить</button>
          </div>
        </div>
        <div class="border rounded p-2 max-h-44 overflow-y-auto" style="border-color: var(--border);">
          <label v-for="city in availableJurisdictions" :key="city" class="flex items-center gap-2 text-[11px] py-0.5" style="color: var(--text-secondary);">
            <input v-model="config.jurisdictions" type="checkbox" :value="city" />
            {{ city }}
          </label>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label class="block text-[11px] mb-1" style="color: var(--text-muted);">Дней назад</label>
          <input v-model.number="config.days_back" type="number" min="1" max="30" class="w-full px-2 py-1.5 border rounded" style="border-color: var(--border);" />
        </div>
        <label class="flex items-center gap-2 text-[11px] mt-6" style="color: var(--text-secondary);">
          <input v-model="config.browser_visible" type="checkbox" />
          Показывать браузер во время парсинга
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
import { applyParserSettingsToNextJobs, createScheduledOperation, getMBPJurisdictions, getParserSettings, updateParserSettings } from '../api'

const availableJurisdictions = ref([])
const config = reactive({
  jurisdictions: [],
  days_back: 7,
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

function selectAll() {
  config.jurisdictions = [...availableJurisdictions.value]
}

function clearAll() {
  config.jurisdictions = []
}

async function loadSettings() {
  const jurisdictionData = await getMBPJurisdictions()
  availableJurisdictions.value = jurisdictionData.jurisdictions || []

  const settings = await getParserSettings('mybuilding')
  Object.assign(config, settings.config || {})
  Object.assign(channels, settings.channels || {})

  if (!Array.isArray(config.jurisdictions)) {
    config.jurisdictions = []
  }
}

async function saveSettings() {
  saving.value = true
  message.value = ''
  try {
    await updateParserSettings('mybuilding', {
      config: {
        ...config,
        jurisdictions: [...config.jurisdictions],
      },
      channels: { ...channels },
    })
    const result = await applyParserSettingsToNextJobs({
      parser_type: 'mybuilding',
      config: {
        ...config,
        jurisdictions: [...config.jurisdictions],
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
      operation_type: 'mybuilding',
      run_at_utc: runAtUtc,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      payload: {
        ...config,
        jurisdictions: [...config.jurisdictions],
      },
      channels: { ...channels },
      fixed_settings: {
        source: 'MyBuildingPermit',
        parse_all_selected_cities: true,
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
