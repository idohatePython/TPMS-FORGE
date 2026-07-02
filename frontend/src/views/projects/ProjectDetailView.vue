<template>
  <section class="page">
    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div v-if="project" class="page-heading">
      <div>
        <p class="eyebrow">PROJECT DETAIL</p>
        <h1>{{ project.name }}</h1>
        <p>{{ project.modelFile }} / {{ project.material }} / {{ project.updatedAt }}</p>
      </div>
      <NSpace>
        <NButton @click="router.push(`/projects/${project.id}/upload`)">上传模型</NButton>
        <NButton type="primary" @click="router.push(`/projects/${project.id}/tpms`)">生成 TPMS</NButton>
      </NSpace>
    </div>

    <NSpin v-if="loading" size="large" />

    <div v-if="project" class="grid-3">
      <NCard title="原始模型" :bordered="false">
        <p class="muted">模型预览与文件元信息将在后端文件服务接入后展示。</p>
      </NCard>
      <NCard title="TPMS 生成" :bordered="false">
        <p class="muted">保存结构类型、参数、任务进度与生成结果。</p>
      </NCard>
      <NCard title="切片输出" :bordered="false">
        <p class="muted">保存切片配置、路径预览和 G-code 下载记录。</p>
      </NCard>
    </div>

    <NCard v-if="project" title="关联任务" :bordered="false">
      <NList>
        <NListItem v-for="task in relatedTasks" :key="task.id">
          <NThing :title="task.name" :description="`${task.type} / ${task.updatedAt}`">
            <template #header-extra>
              <NTag :type="task.status === 'completed' ? 'success' : 'info'">{{ task.status }}</NTag>
            </template>
          </NThing>
        </NListItem>
      </NList>
    </NCard>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { NAlert, NButton, NCard, NList, NListItem, NSpace, NSpin, NTag, NThing } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { getProjectApi, listProjectTasksApi } from '@/api/workspace'
import type { ForgeTask, Project } from '@/types/domain'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const relatedTasks = ref<ForgeTask[]>([])
const loading = ref(false)
const errorMessage = ref('')

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
