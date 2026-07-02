import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import PublicLayout from '@/layouts/PublicLayout.vue'
import { useAuthStore, type UserRole } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    roles?: UserRole[]
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: PublicLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/HomeView.vue'),
          meta: { title: '首页' },
        },
        {
          path: 'demo',
          name: 'demo',
          component: () => import('@/views/DemoView.vue'),
          meta: { title: '访客 Demo' },
        },
        {
          path: 'login',
          name: 'login',
          component: () => import('@/views/LoginView.vue'),
          meta: { title: '登录' },
        },
        {
          path: 'dev/health',
          name: 'dev-health',
          component: () => import('@/views/DevHealthView.vue'),
          meta: { title: '健康检查' },
        },
      ],
    },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: '工作台' },
        },
        {
          path: 'projects',
          name: 'projects',
          component: () => import('@/views/projects/ProjectListView.vue'),
          meta: { title: '项目管理' },
        },
        {
          path: 'projects/:id',
          name: 'project-detail',
          component: () => import('@/views/projects/ProjectDetailView.vue'),
          meta: { title: '项目详情' },
        },
        {
          path: 'projects/:id/upload',
          name: 'project-upload',
          component: () => import('@/views/projects/ProjectUploadView.vue'),
          meta: { title: '模型上传' },
        },
        {
          path: 'projects/:id/tpms',
          name: 'project-tpms',
          component: () => import('@/views/projects/ProjectTpmsView.vue'),
          meta: { title: 'TPMS 生成' },
        },
        {
          path: 'model-tasks/:id',
          name: 'model-task',
          component: () => import('@/views/tasks/ModelTaskView.vue'),
          meta: { title: '模型任务' },
        },
        {
          path: 'projects/:id/slicing',
          name: 'project-slicing',
          component: () => import('@/views/projects/ProjectSlicingView.vue'),
          meta: { title: '切片配置' },
        },
        {
          path: 'slicing-tasks/:id',
          name: 'slicing-task',
          component: () => import('@/views/tasks/SlicingTaskView.vue'),
          meta: { title: '切片任务' },
        },
        {
          path: 'admin',
          name: 'admin',
          component: () => import('@/views/admin/AdminOverviewView.vue'),
          meta: { title: '管理员', roles: ['admin'] },
        },
        {
          path: 'admin/users',
          name: 'admin-users',
          component: () => import('@/views/admin/AdminUsersView.vue'),
          meta: { title: '用户管理', roles: ['admin'] },
        },
        {
          path: 'admin/tasks',
          name: 'admin-tasks',
          component: () => import('@/views/admin/AdminTasksView.vue'),
          meta: { title: '任务审计', roles: ['admin'] },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const title = to.meta.title ? `${to.meta.title} - TPMS-FORGE` : 'TPMS-FORGE'
  document.title = title

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.roles?.length && !to.meta.roles.includes(auth.role)) {
    return { name: 'dashboard' }
  }

  return true
})

export default router
