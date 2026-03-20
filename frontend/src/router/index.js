import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/Dashboard.vue')
    },
    { path: '/jobs', redirect: '/' },
    { path: '/calls', redirect: '/leads' },
    {
      path: '/zillow',
      name: 'zillow',
      component: () => import('../views/ZillowParse.vue')
    },
    {
      path: '/permits',
      name: 'permits',
      component: () => import('../views/PermitParse.vue')
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: () => import('../views/Analytics.vue')
    },
    {
      path: '/data',
      name: 'data',
      component: () => import('../views/AllData.vue')
    },
    {
      path: '/mybuildingpermit',
      name: 'mybuildingpermit',
      component: () => import('../views/MyBuildingPermit.vue')
    },
    {
      path: '/templates',
      name: 'templates',
      component: () => import('../views/TemplatesTest.vue')
    },
    {
      path: '/leads',
      name: 'leads',
      component: () => import('../views/LeadPipeline.vue')
    }
  ]
})

export default router
