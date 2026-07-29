<template>
  <section class="page dashboard-page">
    <div class="page-heading dashboard-hero">
      <div>
        <p class="eyebrow">ENGINEERING WORKSPACE</p>
        <h1>欢迎回来，{{ auth.user?.username ?? 'researcher' }}</h1>
        <p>继续管理项目、模型生成任务与切片结果。</p>
      </div>
      <NButton secondary @click="router.push('/projects')">管理项目</NButton>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div class="grid-3 dashboard-stats">
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>项目</p>
        <NStatistic :value="dashboardStats.projects" />
        <small>当前账户中的工程项目</small>
      </NCard>
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>运行中</p>
        <NStatistic :value="dashboardStats.runningTasks" />
        <small>正在计算的后台任务</small>
      </NCard>
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>已完成</p>
        <NStatistic :value="dashboardStats.completedTasks" />
        <small>可以继续查看或下载</small>
      </NCard>
    </div>

    <NCard title="最近任务" :bordered="false" class="dashboard-task-card">
      <NDataTable :columns="columns" :data="tasks" :loading="loading" :pagination="false" />
    </NCard>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NAlert, NButton, NCard, NDataTable, NProgress, NStatistic, NTag } from 'naive-ui'
import { h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { getDashboardStatsApi, listProjectsApi, listProjectTasksApi } from '@/api/workspace'
import { useAuthStore } from '@/stores/auth'
import type { ForgeTask } from '@/types/domain'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const errorMessage = ref('')
const dashboardStats = ref({ projects: 0, runningTasks: 0, completedTasks: 0, storageGb: 0 })
const tasks = ref<ForgeTask[]>([])

const columns: DataTableColumns<ForgeTask> = [
  { title: '任务', key: 'name' },
  { title: '类型', key: 'type' },
  {
    title: '状态',
    key: 'status',
    render: (row) => h(NTag, { type: row.status === 'completed' ? 'success' : 'info' }, { default: () => row.status }),
  },
  { title: '进度', key: 'progress', render: (row) => h(NProgress, { percentage: row.progress, showIndicator: false }) },
  { title: '更新时间', key: 'updatedAt' },
]

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [stats, projectList] = await Promise.all([getDashboardStatsApi(), listProjectsApi()])
    const projectTasks = await Promise.all(projectList.map((project) => listProjectTasksApi(project.id)))

    dashboardStats.value = stats
    tasks.value = projectTasks.flat().slice(0, 6)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>
