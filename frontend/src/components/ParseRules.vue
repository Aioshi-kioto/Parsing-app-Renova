<template>
  <div class="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
    <button
      @click="expanded = !expanded"
      class="w-full flex items-center justify-between text-left font-semibold text-blue-900"
    >
      <span>📋 Инструкция: Как получить URL для парсинга</span>
      <span class="text-xl">{{ expanded ? '−' : '+' }}</span>
    </button>
    
    <div v-if="expanded" class="mt-4 space-y-3 text-sm text-gray-700">
      <div>
        <strong>1. Откройте Zillow</strong> в обычном браузере (Chrome/Firefox)
      </div>
      <div>
        <strong>2. Настройте фильтры:</strong>
        <ul class="list-disc list-inside ml-4 mt-1">
          <li>Listing Status: <strong>Sold</strong></li>
          <li>Price: Min <strong>$600,000</strong> (или нужная вам сумма)</li>
          <li>Home Type: <strong>Houses</strong></li>
          <li>Basement: <strong>Unfinished</strong></li>
          <li>Sold in last: <strong>36 months</strong></li>
        </ul>
      </div>
      <div>
        <strong>3. Настройте область на карте:</strong> zoom, границы области поиска
      </div>
      <div>
        <strong>4. Скопируйте URL</strong> из адресной строки браузера
      </div>
      <div>
        <strong>5. Вставьте URL</strong> в поле ниже (по одному на строку, можно несколько)
      </div>
      <div class="bg-yellow-50 border border-yellow-200 rounded p-2 mt-2">
        <strong>⚠️ Важно:</strong> При первом запуске откроется браузер для прохождения капчи Zillow. 
        Пройдите капчу вручную, затем парсинг продолжится автоматически.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const expanded = ref(false)
</script>
