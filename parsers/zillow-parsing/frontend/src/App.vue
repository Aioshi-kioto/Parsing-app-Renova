<template>
  <div class="min-h-screen bg-gray-50">
    <div class="container mx-auto px-4 py-8 max-w-7xl">
      <div class="flex items-center justify-between mb-8">
        <h1 class="text-3xl font-bold text-gray-900">Zillow Parser</h1>
        <nav class="flex gap-4">
          <router-link
            to="/"
            class="px-4 py-2 rounded-lg font-medium transition-colors"
            :class="$route.path === '/' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-200'"
          >
            Парсинг
          </router-link>
          <router-link
            to="/data"
            class="px-4 py-2 rounded-lg font-medium transition-colors"
            :class="$route.path === '/data' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-200'"
          >
            Все данные
          </router-link>
        </nav>
      </div>
      
      <router-view />
    </div>
  </div>
</template>

<script setup>
</script>
