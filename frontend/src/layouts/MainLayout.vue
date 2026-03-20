<template>
  <div class="flex h-screen" style="background: var(--bg-base); color: var(--text-primary);">
    <!-- Sidebar -->
    <aside class="w-60 flex flex-col border-r sidebar-shell" style="background: var(--bg-surface); border-color: var(--border);">
      <!-- Logo -->
      <div class="h-12 flex items-center px-4 border-b" style="border-color: var(--border);">
        <span class="text-xs font-bold tracking-widest uppercase" style="color: var(--accent-cyan);">RENOVA</span>
        <span class="text-xs ml-2" style="color: var(--text-muted);">CRM</span>
      </div>

      <!-- Main Nav -->
      <nav class="flex-1 py-3 overflow-y-auto">
        <div class="px-3 mb-1 sidebar-section-label">
          <span class="text-[9px] font-semibold tracking-widest uppercase" style="color: var(--text-muted);">операции</span>
        </div>
        <router-link
          v-for="item in mainNav"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <span class="nav-prefix">{{ isActive(item.path) ? '>' : ' ' }}</span>
          {{ item.name }}
        </router-link>

        <div class="px-3 mt-4 mb-1 sidebar-section-label">
          <span class="text-[9px] font-semibold tracking-widest uppercase" style="color: var(--text-muted);">данные</span>
        </div>
        <router-link
          v-for="item in dataNav"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <span class="nav-prefix">{{ isActive(item.path) ? '>' : ' ' }}</span>
          {{ item.name }}
        </router-link>

        <!-- Parsers group (collapsible) -->
        <div class="px-3 mt-4 mb-1 flex items-center justify-between cursor-pointer sidebar-section-label" @click="parsersOpen = !parsersOpen">
          <span class="text-[9px] font-semibold tracking-widest uppercase" style="color: var(--text-muted);">парсеры</span>
          <span class="text-[9px]" style="color: var(--text-muted);">{{ parsersOpen ? '[-]' : '[+]' }}</span>
        </div>
        <template v-if="parsersOpen">
          <router-link
            v-for="item in parsersNav"
            :key="item.path"
            :to="item.path"
            class="nav-item pl-6"
            :class="{ active: isActive(item.path) }"
          >
            <span class="nav-prefix">{{ isActive(item.path) ? '>' : ' ' }}</span>
            {{ item.name }}
          </router-link>
        </template>
      </nav>

      <!-- Status -->
      <div class="px-4 py-3 border-t" style="border-color: var(--border);">
        <div class="flex items-center gap-2">
          <span class="w-1.5 h-1.5 inline-block" style="background: var(--accent-green);"></span>
          <span class="text-[10px]" style="color: var(--text-muted);">system online</span>
        </div>
        <div class="text-[9px] mt-1" style="color: var(--text-muted);">v1.1.0</div>
      </div>
    </aside>

    <!-- Main content -->
    <div class="flex-1 overflow-hidden">
      <main class="app-main-content flex-1 overflow-auto p-5">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const parsersOpen = ref(false)

const mainNav = [
  { name: 'Операции', path: '/' },
  { name: 'Лиды', path: '/leads' },
]

const dataNav = [
  { name: 'Аналитика', path: '/analytics' },
  { name: 'Все данные', path: '/data' },
  { name: 'Шаблоны', path: '/templates' },
]

const parsersNav = [
  { name: 'Пермит', path: '/permits' },
  { name: 'MyBuilding', path: '/mybuildingpermit' },
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<style scoped>
.nav-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  border-left: 2px solid transparent;
  transition: all 0.15s;
  cursor: pointer;
}
.nav-item:hover {
  color: var(--text-primary);
  background: var(--bg-elevated);
  border-left-color: var(--border-active);
}
.nav-item.active {
  color: var(--text-primary);
  background: var(--bg-elevated);
  border-left-color: var(--text-primary);
}
.nav-prefix {
  font-size: 11px;
  width: 12px;
  flex-shrink: 0;
  color: var(--accent-blue);
}
.nav-item:not(.active) .nav-prefix {
  color: transparent;
}
.sidebar-shell {
  box-shadow: inset -1px 0 0 var(--border);
}
.sidebar-section-label {
  opacity: 0.88;
}
</style>
