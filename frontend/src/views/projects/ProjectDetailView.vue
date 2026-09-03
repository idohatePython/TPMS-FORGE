<template>
  <section class="page project-detail-page">
    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div v-if="project" class="page-heading project-detail-hero">
      <div>
        <p class="eyebrow">PROJECT DETAIL</p>
        <div v-if="editingName" class="project-name-editor">
          <NInput
            v-model:value="projectName"
            maxlength="80"
            autofocus
            @keyup.enter="saveProjectName"
            @keyup.esc="cancelProjectName"
          />
          <NButton type="primary" :loading="savingName" @click="saveProjectName">保存</NButton>
          <NButton :disabled="savingName" @click="cancelProjectName">取消</NButton>
        </div>
        <div v-else class="project-name-heading">
          <h1>{{ project.name }}</h1>
          <NButton size="small" secondary @click="startProjectNameEdit">编辑名称</NButton>
        </div>
        <p>{{ project.modelFile || '尚未上传模型' }} · {{ project.material }} · {{ project.updatedAt }}</p>
      </div>
      <NSpace>
        <NButton secondary @click="router.push(`/projects/${project.id}/files`)">项目文件</NButton>
        <NButton @click="router.push('/projects')">返回列表</NButton>
        <NButton @click="loadProject">刷新</NButton>
      </NSpace>
    </div>

    <NSpin v-if="loading" size="large" />

    <div v-if="project" class="grid-3 project-summary-grid">
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>项目状态</p>
        <NTag :type="statusTagType(project.status)" round>{{ projectStatusLabel(project.status) }}</NTag>
        <small>{{ nextStepText }}</small>
      </NCard>
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>任务数量</p>
        <NStatistic :value="relatedTasks.length" />
        <small>{{ completedTasks }} 个已完成</small>
      </NCard>
      <NCard :bordered="false" class="dashboard-stat-card">
        <p>模型文件</p>
        <strong class="project-file-name">{{ project.modelFile || '未选择' }}</strong>
        <small>{{ project.modelFile ? '可作为 TPMS 或切片输入' : '请先上传 STL/OBJ' }}</small>
      </NCard>
    </div>

    <div v-if="project" class="project-workflow-grid">
      <article class="dashboard-panel project-step-card">
        <NTag round>1</NTag>
        <div>
          <h2>模型导入</h2>
          <p>从本地导入 STL/OBJ，或选择项目中已有的模型并预览。</p>
        </div>
        <NButton type="primary" secondary @click="router.push(`/projects/${project.id}/upload`)">
          {{ project.modelFile ? '选择模型' : '导入模型' }}
        </NButton>
      </article>

      <article class="dashboard-panel project-step-card">
        <NTag round>2</NTag>
        <div>
          <h2>切片与 G-code</h2>
          <p>在同一工作区选择普通填充或 TPMS 梯度填充，配置参数并生成 G-code。</p>
        </div>
        <NButton :disabled="!project.modelFile" @click="router.push(`/projects/${project.id}/slicing`)">
          进入切片
        </NButton>
      </article>

      <article class="dashboard-panel project-step-card">
        <NTag round>3</NTag>
        <div>
          <h2>项目文件</h2>
          <p>统一管理导入模型、TPMS 生成模型和 G-code，并下载输出。</p>
        </div>
        <NButton @click="router.push(`/projects/${project.id}/files`)">查看与下载</NButton>
      </article>
    </div>

    <section v-if="project" class="dashboard-panel project-task-panel">
      <div class="dashboard-panel-heading">
        <div>
          <p class="eyebrow">TASKS</p>
          <h2>关联任务</h2>
        </div>
        <NButton size="small" @click="router.push(`/projects/${project.id}/files`)">文件管理</NButton>
      </div>

      <NList v-if="relatedTasks.length">
        <NListItem v-for="task in relatedTasks" :key="task.id">
          <NThing :title="task.name" :description="`${taskTypeLabel(task.type)} · ${task.updatedAt}`">
            <template #header-extra>
              <NSpace align="center">
                <NTag :type="statusTagType(task.status)" round>{{ statusLabel(task.status) }}</NTag>
                <NButton size="small" @click="openTask(task)">查看</NButton>
              </NSpace>
            </template>
          </NThing>
        </NListItem>
      </NList>
      <NEmpty v-else description="暂无任务，完成上传后可在切片工作区创建任务" />
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NEmpty,
  NList,
  NListItem,
  NInput,
  NSpace,
  NSpin,
  NStatistic,
  NTag,
  NThing,
} from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { getProjectApi, listProjectTasksApi, updateProjectNameApi } from '@/api/workspace'
import type { ForgeTask, Project, TaskStatus } from '@/types/domain'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const relatedTasks = ref<ForgeTask[]>([])
const loading = ref(false)
const errorMessage = ref('')
const editingName = ref(false)
const savingName = ref(false)
const projectName = ref('')

const completedTasks = computed(() => relatedTasks.value.filter((task) => task.status === 'completed').length)
const nextStepText = computed(() => {
  if (!project.value?.modelFile) return '下一步：上传模型'
  if (!relatedTasks.value.some((task) => task.type === 'slicing-gcode')) return '下一步：进入切片并选择填充方式'
  return '输出已生成，可在项目文件中下载'
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

function openTask(task: ForgeTask) {
  router.push(task.type === 'model-generation' ? `/model-tasks/${task.id}` : `/slicing-tasks/${task.id}`)
}

function startProjectNameEdit() {
  projectName.value = project.value?.name ?? ''
  editingName.value = true
}

function cancelProjectName() {
  editingName.value = false
  projectName.value = project.value?.name ?? ''
}

async function saveProjectName() {
  if (!project.value || savingName.value) return

  const name = projectName.value.trim()
  if (!name) {
    errorMessage.value = '项目名称不能为空'
    return
  }

  savingName.value = true
  errorMessage.value = ''
  try {
    project.value = await updateProjectNameApi(project.value.id, name)
    editingName.value = false
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    savingName.value = false
  }
}

async function loadProject() {
  const projectId = String(route.params.id)
  loading.value = true
  errorMessage.value = ''

  try {
    const [projectData, taskData] = await Promise.all([
      getProjectApi(projectId),
      listProjectTasksApi(projectId),
    ])
    project.value = projectData
    relatedTasks.value = taskData
  } catch (error) {
    project.value = null
    relatedTasks.value = []
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

onMounted(loadProject)
watch(() => route.params.id, loadProject)
</script>
