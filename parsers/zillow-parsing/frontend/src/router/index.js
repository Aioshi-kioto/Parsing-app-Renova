import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Parse',
    component: () => import('../views/ParseView.vue'),
    meta: { title: 'Парсинг' }
  },
  {
    path: '/data',
    name: 'AllData',
    component: () => import('../views/AllDataView.vue'),
    meta: { title: 'Все данные' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} — Zillow Parser` : 'Zillow Parser'
})

export default router
