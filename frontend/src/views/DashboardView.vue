<template>
  <section class="page dashboard-page">
    <div class="page-heading dashboard-hero">
      <div>
        <p class="eyebrow">ENGINEERING WORKSPACE</p>
        <h1>欢迎回来，{{ auth.user?.username ?? 'researcher' }}</h1>
        <p>从模型导入到普通或 TPMS 梯度切片，继续推进当前项目。</p>
      </div>
      <NSpace>
        <NButton secondary @click="loadDashboard">刷新</NButton>
        <NButton secondary @click="router.push('/projects')">管理项目</NButton>
      </NSpace>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div class="grid-3 dashboard-stats">
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>项目</p>
        <NStatistic :value="dashboardStats.projects" />
        <small>{{ activeProjects }} 个项目仍在推进</small>
      </NCard>
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>待处理</p>
        <NStatistic :value="dashboardStats.runningTasks" />
        <small>包含排队和运行中的任务</small>
      </NCard>
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>已完成</p>
        <NStatistic :value="dashboardStats.completedTasks" />
        <small>可继续查看模型或切片结果</small>
      </NCard>
    </div>

    <div class="dashboard-work-grid">
      <section class="dashboard-panel dashboard-focus-panel">
        <div class="dashboard-panel-heading">
          <div>
            <p class="eyebrow">FOCUS</p>
            <h2>当前重点</h2>
          </div>
          <NTag v-if="focusTask" :type="statusTagType(focusTask.status)" round>
            {{ statusLabel(focusTask.status) }}
          </NTag>
        </div>

        <div v-if="focusTask && focusProject" class="dashboard-focus">
          <div>
            <strong>{{ focusTask.name }}</strong>
            <span>{{ focusProject.name }} · {{ taskTypeLabel(focusTask.type) }}</span>
          </div>
          <NProgress
            type="line"
            :percentage="focusTask.progress"
            :status="focusTask.status === 'failed' ? 'error' : 'success'"
          />
          <div class="dashboard-focus-actions">
            <NButton size="small" @click="openProject(focusProject.id)">查看项目</NButton>
            <NButton size="small" type="primary" @click="openTask(focusTask)">查看任务</NButton>
          </div>
        </div>

        <NEmpty v-else description="暂无需要处理的任务" />
      </section>

      <section class="dashboard-panel">
        <div class="dashboard-panel-heading">
          <div>
            <p class="eyebrow">PROJECTS</p>
            <h2>活跃项目</h2>
          </div>
          <NButton size="small" text @click="router.push('/projects')">全部项目</NButton>
        </div>

        <div v-if="projects.length" class="dashboard-project-list">
          <article v-for="project in projects.slice(0, 4)" :key="project.id" class="dashboard-project-row">
            <div>
              <strong>{{ project.name }}</strong>
              <span>{{ project.modelFile || '尚未上传模型' }} · {{ project.material }}</span>
            </div>
            <div class="dashboard-project-actions">
              <NTag :type="statusTagType(project.status)" round>{{ projectStatusLabel(project.status) }}</NTag>
              <NButton size="small" @click="openProject(project.id)">打开</NButton>
            </div>
          </article>
        </div>

        <NEmpty v-else-if="!loading" description="暂无项目" />
      </section>
    </div>

    <section class="dashboard-panel dashboard-task-card">
      <div class="dashboard-panel-heading">
        <div>
          <p class="eyebrow">TASK QUEUE</p>
          <h2>最近任务</h2>
        </div>
        <NTag round>{{ tasks.length }} 条</NTag>
      </div>
      <NDataTable :columns="columns" :data="tasks" :loading="loading" :pagination="false" />
    </section>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NAlert, NButton, NCard, NDataTable, NEmpty, NProgress, NSpace, NStatistic, NTag } from 'naive-ui'
import { computed, h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { getDashboardStatsApi, listProjectsApi, listProjectTasksApi } from '@/api/workspace'
import { useAuthStore } from '@/stores/auth'
import type { ForgeTask, Project, TaskStatus } from '@/types/domain'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const errorMessage = ref('')
const dashboardStats = ref({ projects: 0, runningTasks: 0, completedTasks: 0, storageGb: 0 })
const projects = ref<Project[]>([])
const tasks = ref<ForgeTask[]>([])

const columns: DataTableColumns<ForgeTask> = [
  {
    title: '任务',
    key: 'name',
    render: (row) =>
      h(
        'button',
        { class: 'table-link-button', onClick: () => openTask(row) },
        row.name,
      ),
  },
  { title: '类型', key: 'type', render: (row) => taskTypeLabel(row.type) },
  {
    title: '状态',
    key: 'status',
    render: (row) =>
      h(NTag, { type: statusTagType(row.status), round: true }, { default: () => statusLabel(row.status) }),
  },
  {
    title: '进度',
    key: 'progress',
    render: (row) =>
      h(NProgress, {
        percentage: row.progress,
        showIndicator: false,
        status: row.status === 'failed' ? 'error' : 'success',
      }),
  },
  { title: '更新时间', key: 'updatedAt' },
]

const activeProjects = computed(() => projects.value.filter((project) => project.status !== 'completed').length)
const focusTask = computed(() => {
  return (
    tasks.value.find((task) => task.status === 'running') ??
    tasks.value.find((task) => task.status === 'queued') ??
    tasks.value[0] ??
    null
  )
})
const focusProject = computed(() => {
  if (!focusTask.value) return null
  return projects.value.find((project) => project.id === focusTask.value?.projectId) ?? null
})

function statusLabel(status: TaskStatus) {
  const labels: Record<TaskStatus, string> = {
    queued: '排队中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
  }
  return labels[status]
}

function projectStatusLabel(status: TaskStatus) {
  if (status === 'queued') return '待处理'
  return statusLabel(status)
}

function statusTagType(status: TaskStatus) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'running') return 'info'
  return 'warning'
}

function taskTypeLabel(type: ForgeTask['type']) {
  return type === 'model-generation' ? 'TPMS 生成' : '切片 G-code'
}

function openProject(projectId: string) {
  router.push(`/projects/${projectId}`)
}

function openTask(task: ForgeTask) {
  router.push(task.type === 'model-generation' ? `/model-tasks/${task.id}` : `/slicing-tasks/${task.id}`)
}

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [stats, projectList] = await Promise.all([getDashboardStatsApi(), listProjectsApi()])
    const projectTasks = await Promise.all(projectList.map((project) => listProjectTasksApi(project.id)))

    dashboardStats.value = stats
    projects.value = projectList
    tasks.value = projectTasks
      .flat()
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
      .slice(0, 8)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>
