<template>
  <div class="mb-6">
    <label class="block text-sm font-medium text-gray-700 mb-2">
      URL для парсинга (по одному на строку)
    </label>
    <textarea
      v-model="urlsText"
      @input="validateUrls"
      rows="6"
      class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
      placeholder="Вставьте URL из Zillow (по одному на строку)&#10;Например:&#10;https://www.zillow.com/seattle-wa/sold/..."
    ></textarea>
    <div v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</div>
    <div v-if="validUrls.length > 0" class="mt-2 text-sm text-green-600">
      ✓ Найдено валидных URL: {{ validUrls.length }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: String
})

const emit = defineEmits(['update:modelValue', 'urls-changed'])

const urlsText = ref(props.modelValue || '')
const error = ref('')
const validUrls = ref([])

function validateUrls() {
  emit('update:modelValue', urlsText.value)
  
  const lines = urlsText.value.split('\n').map(s => s.trim()).filter(s => s)
  validUrls.value = lines.filter(url => url.includes('zillow.com'))
  
  if (lines.length > 0 && validUrls.value.length === 0) {
    error.value = 'Не найдено валидных URL Zillow'
  } else {
    error.value = ''
  }
  
  emit('urls-changed', validUrls.value)
}

watch(() => props.modelValue, (newVal) => {
  urlsText.value = newVal || ''
  validateUrls()
})
</script>
