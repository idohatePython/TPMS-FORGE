<template>
  <section class="page project-list-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">PROJECTS</p>
        <h1>项目管理</h1>
        <p>项目承载模型文件、TPMS 结果、切片任务和后续打印路径检查。</p>
      </div>
      <NSpace>
        <NButton :loading="loading" @click="loadProjects">刷新</NButton>
        <NButton type="primary" @click="showCreateModal = true">新建项目</NButton>
      </NSpace>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div class="grid-3 project-summary-grid">
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>项目总数</p>
        <NStatistic :value="projects.length" />
        <small>当前账户可访问项目</small>
      </NCard>
      <NCard
        :bordered="false"
        class="dashboard-stat-card project-stat-link"
        role="button"
        tabindex="0"
        @click="openExistingModel"
        @keyup.enter="openExistingModel"
      >
        <p>已有模型</p>
        <NStatistic :value="projectsWithModel" />
        <small>{{ projectsWithModel ? '点击进入模型预览' : '暂无可预览模型' }}</small>
      </NCard>
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>待处理</p>
        <NStatistic :value="pendingProjects" />
        <small>需要上传模型或继续配置</small>
      </NCard>
    </div>

    <section class="dashboard-panel project-table-panel">
      <div class="dashboard-panel-heading">
        <div>
          <p class="eyebrow">PROJECT INDEX</p>
          <h2>项目列表</h2>
        </div>
        <NTag round>{{ projects.length }} 个</NTag>
      </div>
      <NDataTable
        v-if="projects.length || loading"
        :columns="columns"
        :data="projects"
        :loading="loading"
        :pagination="false"
      />
      <NEmpty v-else description="暂无项目" />
    </section>

    <NModal v-model:show="showCreateModal" preset="card" title="新建项目" class="project-create-modal">
      <NForm label-placement="top">
        <NFormItem label="项目名称" required>
          <NInput v-model:value="createForm.name" maxlength="80" placeholder="例如：梯度 TPMS 鞋垫" @keyup.enter="createProject" />
        </NFormItem>
        <NFormItem label="打印材料">
          <NSelect v-model:value="createForm.material" :options="materialOptions" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCreateModal = false">取消</NButton>
          <NButton type="primary" :loading="creating" :disabled="!createForm.name.trim()" @click="createProject">创建并导入模型</NButton>
        </NSpace>
      </template>
    </NModal>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NAlert, NButton, NCard, NDataTable, NEmpty, NForm, NFormItem, NInput, NModal, NSelect, NSpace, NStatistic, NTag } from 'naive-ui'
import { computed, h, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { createProjectApi, listProjectsApi } from '@/api/workspace'
import type { Project, TaskStatus } from '@/types/domain'

const router = useRouter()
const projects = ref<Project[]>([])
const loading = ref(false)
const errorMessage = ref('')
const showCreateModal = ref(false)
const creating = ref(false)
const createForm = reactive({ name: '', material: 'PLA' })
const materialOptions = ['PLA', 'PETG', 'TPU', 'ABS', 'ASA', 'PA-CF', 'Resin'].map((value) => ({ label: value, value }))

const projectsWithModel = computed(() => projects.value.filter((project) => project.modelFile).length)
const pendingProjects = computed(() => projects.value.filter((project) => project.status !== 'completed').length)

function statusLabel(status: TaskStatus) {
  const labels: Record<TaskStatus, string> = {
    queued: '待处理',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
  }
  return labels[status]
}

function statusTagType(status: TaskStatus) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'running') return 'info'
  return 'warning'
}

function nextAction(project: Project) {
  if (!project.modelFile) return '上传模型'
  if (project.status !== 'completed') return '继续项目'
  return '查看项目'
}

function openNext(project: Project) {
  if (!project.modelFile) {
    router.push(`/projects/${project.id}/upload`)
    return
  }
  if (project.status !== 'completed') {
    router.push(`/projects/${project.id}`)
    return
  }
  router.push(`/projects/${project.id}`)
}

function openExistingModel() {
  const modelProjects = projects.value.filter((project) => project.modelFile)
  if (!modelProjects.length) return

  const rememberedProjectId = localStorage.getItem('tpms-forge-active-project')
  const target = modelProjects.find((project) => project.id === rememberedProjectId) ?? modelProjects[0]
  router.push(`/projects/${target.id}/upload`)
}

const columns: DataTableColumns<Project> = [
  {
    title: '项目名称',
    key: 'name',
    render: (row) =>
      h(
        'button',
        { class: 'table-link-button', onClick: () => router.push(`/projects/${row.id}`) },
        row.name,
      ),
  },
  {
    title: '模型文件',
    key: 'modelFile',
    render: (row) => row.modelFile
      ? h(
        'button',
        {
          class: 'table-link-button',
          title: `预览 ${row.modelFile}`,
          onClick: () => router.push(`/projects/${row.id}/upload`),
        },
        row.modelFile,
      )
      : h('span', { class: 'muted' }, '尚未上传'),
  },
  { title: '材料', key: 'material' },
  {
    title: '状态',
    key: 'status',
    render: (row) =>
      h(NTag, { type: statusTagType(row.status), round: true }, { default: () => statusLabel(row.status) }),
  },
  { title: '更新时间', key: 'updatedAt' },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row) => h(NButton, { size: 'small', onClick: () => openNext(row) }, { default: () => nextAction(row) }),
  },
]

async function loadProjects() {
  loading.value = true
  errorMessage.value = ''

  try {
    projects.value = await listProjectsApi()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

async function createProject() {
  const name = createForm.name.trim()
  if (!name || creating.value) return
  creating.value = true
  errorMessage.value = ''
  try {
    const project = await createProjectApi(name, createForm.material)
    showCreateModal.value = false
    createForm.name = ''
    await router.push(`/projects/${project.id}/upload`)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    creating.value = false
  }
}

onMounted(loadProjects)
</script>
