<template>
  <div class="space-y-4 animate-fadeIn">
    <div class="flex items-center justify-between">
      <div>
        <div class="text-[9px] mb-1" style="color: var(--text-muted);">/шаблоны/тесты</div>
        <h1 class="text-xl font-bold tracking-wide" style="color: var(--text-primary);">ШАБЛОНЫ И ТЕСТЫ</h1>
      </div>
      <button class="btn-secondary" @click="loadTemplates">Обновить</button>
    </div>

    <div class="card p-4 space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label class="text-[10px] block mb-1" style="color: var(--text-muted);">Тип клиента (кейс)</label>
          <select v-model="selectedCase" class="w-full">
            <option v-for="t in templates" :key="t.case_type" :value="t.case_type">{{ t.case_type }}</option>
          </select>
        </div>
        <div>
          <label class="text-[10px] block mb-1" style="color: var(--text-muted);">Текущий шаблон</label>
          <div class="text-[11px] py-2 px-3 border rounded" style="border-color: var(--border); color: var(--text-primary); background: var(--bg-elevated);">
            {{ selectedCase || '—' }}
          </div>
        </div>
      </div>

      <div class="flex gap-0 border-b" style="border-color: var(--border);">
        <button class="terminal-tab" :class="{ active: activeChannel === 'email' }" @click="activeChannel = 'email'">Email</button>
        <button class="terminal-tab" :class="{ active: activeChannel === 'lob' }" @click="activeChannel = 'lob'">Lob (письмо)</button>
        <button class="terminal-tab" :class="{ active: activeChannel === 'sms' }" @click="activeChannel = 'sms'">SMS</button>
      </div>

      <div v-if="activeChannel === 'email'" class="space-y-3">
        <div>
          <label class="text-[10px] block mb-1" style="color: var(--text-muted);">Тема Email</label>
          <input v-model="form.email_subject" type="text" class="w-full" />
        </div>
        <div>
          <label class="text-[10px] block mb-1" style="color: var(--text-muted);">Текст Email</label>
          <textarea v-model="form.email_body" rows="9" class="w-full"></textarea>
        </div>
      </div>

      <div v-else-if="activeChannel === 'lob'" class="space-y-3">
        <div>
          <label class="text-[10px] block mb-1" style="color: var(--text-muted);">Lob template ID (tmpl_...)</label>
          <input v-model="form.lob_template_id" type="text" class="w-full" placeholder="tmpl_xxx..." />
        </div>
        <div>
          <label class="text-[10px] block mb-1" style="color: var(--text-muted);">Lob HTML (опционально)</label>
          <textarea v-model="form.lob_body_html" rows="8" class="w-full" placeholder="<html>...</html>"></textarea>
        </div>
      </div>

      <div v-else class="space-y-3">
        <div>
          <label class="text-[10px] block mb-1" style="color: var(--text-muted);">Текст SMS</label>
          <textarea v-model="form.sms_body" rows="5" class="w-full"></textarea>
        </div>
      </div>

      <p class="text-[10px]" style="color: var(--text-muted);">
        Доступные переменные: <code>{owner_name}</code>, <code>{street_name}</code>, <code>{address}</code>.
      </p>

      <div class="pt-2 border-t" style="border-color: var(--border);">
        <button class="btn-primary" :disabled="saving" @click="saveTemplate">
          {{ saving ? 'Сохранение...' : 'Применить ко всем' }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="card p-4 space-y-3">
        <h2 class="text-[11px] font-semibold uppercase tracking-wide" style="color: var(--text-secondary);">Тест Email</h2>
        <input v-model="testEmail.to_email" type="email" class="w-full" placeholder="test@example.com" />
        <input v-model="testEmail.owner_name" type="text" class="w-full" placeholder="Имя владельца" />
        <input v-model="testEmail.street_name" type="text" class="w-full" placeholder="Street name" />
        <input v-model="testEmail.address" type="text" class="w-full" placeholder="Полный адрес" />
        <button class="btn-secondary" :disabled="testingEmail" @click="sendEmailTest">
          {{ testingEmail ? 'Отправка...' : 'Отправить тест' }}
        </button>
      </div>

      <div class="card p-4 space-y-3">
        <h2 class="text-[11px] font-semibold uppercase tracking-wide" style="color: var(--text-secondary);">Тест Lob</h2>
        <input v-model="testLob.recipient_name" type="text" class="w-full" placeholder="Имя получателя" />
        <input v-model="testLob.address_line1" type="text" class="w-full" placeholder="Address line 1" />
        <div class="grid grid-cols-3 gap-2">
          <input v-model="testLob.address_city" type="text" class="w-full" placeholder="City" />
          <input v-model="testLob.address_state" type="text" class="w-full" placeholder="State" />
          <input v-model="testLob.address_zip" type="text" class="w-full" placeholder="ZIP" />
        </div>
        <input v-model="testLob.street_name" type="text" class="w-full" placeholder="Street name" />
        <input v-model="testLob.address" type="text" class="w-full" placeholder="Полный адрес" />
        <button class="btn-secondary" :disabled="testingLob" @click="sendLobTest">
          {{ testingLob ? 'Отправка...' : 'Отправить тестовое письмо' }}
        </button>
      </div>
    </div>

    <div v-if="message" class="card p-3 text-[10px]" :style="{ color: message.ok ? 'var(--accent-green)' : 'var(--accent-red)' }">
      {{ message.text }}
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  getOutboundTemplates,
  updateOutboundTemplate,
  sendOutboundTestEmail,
  sendOutboundTestLob,
} from '../api'

const templates = ref([])
const selectedCase = ref('')
const activeChannel = ref('email')
const saving = ref(false)
const testingEmail = ref(false)
const testingLob = ref(false)
const message = ref(null)

const form = reactive({
  email_subject: '',
  email_body: '',
  sms_body: '',
  lob_template_id: '',
  lob_body_html: '',
})

const testEmail = reactive({
  to_email: '',
  owner_name: '',
  street_name: '',
  address: '',
})

const testLob = reactive({
  recipient_name: 'Homeowner',
  address_line1: '',
  address_city: '',
  address_state: 'WA',
  address_zip: '',
  owner_name: '',
  street_name: '',
  address: '',
})

const selectedTemplate = computed(() => templates.value.find((t) => t.case_type === selectedCase.value))

watch(selectedTemplate, (tpl) => {
  if (!tpl) return
  form.email_subject = tpl.email_subject || ''
  form.email_body = tpl.email_body || ''
  form.sms_body = tpl.sms_body || ''
  form.lob_template_id = tpl.lob_template_id || ''
  form.lob_body_html = tpl.lob_body_html || ''
}, { immediate: true })

async function loadTemplates() {
  try {
    const res = await getOutboundTemplates()
    templates.value = res.templates || []
    if (!selectedCase.value && templates.value.length) selectedCase.value = templates.value[0].case_type
  } catch (e) {
    message.value = { ok: false, text: `Ошибка загрузки шаблонов: ${e.message}` }
  }
}

async function saveTemplate() {
  if (!selectedCase.value) return
  saving.value = true
  message.value = null
  try {
    await updateOutboundTemplate(selectedCase.value, {
      email_subject: form.email_subject,
      email_body: form.email_body,
      sms_body: form.sms_body,
      lob_template_id: form.lob_template_id || null,
      lob_body_html: form.lob_body_html || null,
    })
    await loadTemplates()
    message.value = { ok: true, text: `Шаблон ${selectedCase.value} обновлён и применён для всех операций.` }
  } catch (e) {
    message.value = { ok: false, text: `Ошибка сохранения: ${e.message}` }
  } finally {
    saving.value = false
  }
}

async function sendEmailTest() {
  testingEmail.value = true
  message.value = null
  try {
    const res = await sendOutboundTestEmail({
      case_type: selectedCase.value || 'GENERAL',
      to_email: testEmail.to_email,
      owner_name: testEmail.owner_name,
      street_name: testEmail.street_name,
      address: testEmail.address,
      subject_override: form.email_subject,
      body_override: form.email_body,
    })
    message.value = { ok: true, text: `Тестовое Email отправлено. ID: ${res.message_id || 'ok'}` }
  } catch (e) {
    message.value = { ok: false, text: `Ошибка тестовой отправки Email: ${e.message}` }
  } finally {
    testingEmail.value = false
  }
}

async function sendLobTest() {
  testingLob.value = true
  message.value = null
  try {
    const res = await sendOutboundTestLob({
      case_type: selectedCase.value || 'GENERAL',
      recipient_name: testLob.recipient_name,
      address_line1: testLob.address_line1,
      address_city: testLob.address_city,
      address_state: testLob.address_state,
      address_zip: testLob.address_zip,
      owner_name: testLob.owner_name || testLob.recipient_name,
      street_name: testLob.street_name,
      address: testLob.address || testLob.address_line1,
      lob_template_override: form.lob_template_id || form.lob_body_html || null,
    })
    message.value = { ok: true, text: `Тестовое письмо Lob отправлено. ID: ${res.lob_id || 'ok'}` }
  } catch (e) {
    message.value = { ok: false, text: `Ошибка тестовой отправки Lob: ${e.message}` }
  } finally {
    testingLob.value = false
  }
}

onMounted(loadTemplates)
</script>
