<template>
  <section class="page">
    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div v-if="task" class="page-heading">
      <div>
        <p class="eyebrow">SLICING TASK</p>
        <h1>{{ task.name }}</h1>
        <p>查看一次切片工作流的输入、TPMS 中间阶段和 G-code 输出。</p>
      </div>
      <NSpace>
        <NButton @click="router.push(`/projects/${task.projectId}/files`)">项目文件</NButton>
        <NButton v-if="task.status === 'failed'" type="primary" @click="router.push(`/projects/${task.projectId}/slicing`)">返回重试</NButton>
        <NButton v-else :disabled="task.status !== 'completed' || !task.outputFilename" type="primary" @click="downloadGcode">下载 G-code</NButton>
      </NSpace>
    </div>

    <NSpin v-if="loading" size="large" />

    <NAlert v-if="task?.errorMessage" type="error" title="工作流执行失败">
      {{ task.errorMessage }}
    </NAlert>

    <div v-if="task" class="grid-2 task-workflow-grid">
      <NCard title="执行阶段" :bordered="false">
        <NSteps vertical :current="currentStep" :status="stepStatus">
          <NStep title="输入模型" :description="task.inputFilename ?? '项目当前模型'" />
          <NStep v-if="isTpmsWorkflow" title="TPMS 填充生成" :description="task.intermediateFilename ?? stageDescription" />
          <NStep title="G-code 切片" :description="task.outputFilename ?? stageDescription" />
        </NSteps>
        <NProgress type="line" :percentage="task.progress" :status="task.status === 'failed' ? 'error' : 'default'" />
      </NCard>
      <NCard title="输出摘要" :bordered="false">
        <NDescriptions :column="1">
          <NDescriptionsItem label="任务状态">{{ statusLabel }}</NDescriptionsItem>
          <NDescriptionsItem label="当前阶段">{{ stageDescription }}</NDescriptionsItem>
          <NDescriptionsItem v-if="task.inputFilename" label="输入模型">{{ task.inputFilename }}</NDescriptionsItem>
          <NDescriptionsItem v-if="task.intermediateFilename" label="TPMS STL">{{ task.intermediateFilename }}</NDescriptionsItem>
          <NDescriptionsItem v-if="task.outputFilename" label="G-code">{{ task.outputFilename }}</NDescriptionsItem>
          <NDescriptionsItem label="Firmware">Marlin</NDescriptionsItem>
          <NDescriptionsItem label="更新时间">{{ task.updatedAt }}</NDescriptionsItem>
        </NDescriptions>
      </NCard>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NAlert, NButton, NCard, NDescriptions, NDescriptionsItem, NProgress, NSpace, NSpin, NStep, NSteps } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { loadAuthToken, normalizeApiError } from '@/api/client'
import { getSlicingTaskApi } from '@/api/workspace'
import type { ForgeTask } from '@/types/domain'

const route = useRoute()
const router = useRouter()
const task = ref<ForgeTask | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const isTpmsWorkflow = computed(() => Boolean(task.value?.intermediateFilename || task.value?.stage?.includes('tpms')))
const currentStep = computed(() => {
  if (!task.value) return 1
  if (task.value.stage?.includes('tpms')) return 2
  if (task.value.stage?.includes('gcode')) return isTpmsWorkflow.value ? 3 : 2
  return isTpmsWorkflow.value ? 3 : 2
})
const stepStatus = computed(() => task.value?.status === 'failed' ? 'error' : task.value?.status === 'completed' ? 'finish' : 'process')
const statusLabel = computed(() => ({ queued: '排队中', running: '执行中', completed: '已完成', failed: '失败' })[task.value?.status ?? 'queued'])
const stageDescription = computed(() => {
  const stage = task.value?.stage
  if (stage === 'tpms-generation') return '正在生成 TPMS 填充 STL'
  if (stage === 'tpms-generation-failed') return 'TPMS 生成失败'
  if (stage === 'gcode-slicing') return '正在生成 G-code'
  if (stage === 'gcode-slicing-failed') return 'G-code 切片失败，中间 STL 已保留'
  if (stage === 'completed') return '所有阶段已完成'
  return '等待执行'
})

async function downloadGcode() {
  if (!task.value?.outputFilename) return
  try {
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
    const response = await fetch(`${baseUrl}/slicing-tasks/${task.value.id}/gcode`, {
      headers: { Authorization: `Bearer ${loadAuthToken()}` },
    })
    if (!response.ok) throw new Error(`G-code 下载失败：${response.status}`)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = task.value.outputFilename
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'G-code 下载失败'
  }
}

async function loadTask() {
  loading.value = true
  errorMessage.value = ''

  try {
    task.value = await getSlicingTaskApi(String(route.params.id))
  } catch (error) {
    task.value = null
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

onMounted(loadTask)
watch(() => route.params.id, loadTask)
</script>
