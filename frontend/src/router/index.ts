import { createRouter, createWebHistory } from 'vue-router'

import DevHealthView from '@/views/DevHealthView.vue'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/dev/health', name: 'dev-health', component: DevHealthView },
  ],
})

export default router
