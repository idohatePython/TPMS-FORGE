<template>
  <section class="page">
    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div v-if="task" class="page-heading">
      <div>
        <p class="eyebrow">MODEL TASK</p>
        <h1>{{ task.name }}</h1>
        <p>模型生成任务详情页，后续接入任务日志、预览文件和失败原因。</p>
      </div>
      <NTag :type="task.status === 'completed' ? 'success' : 'info'" round>{{ task.status }}</NTag>
    </div>

    <NSpin v-if="loading" size="large" />

    <NCard v-if="task" :bordered="false">
      <NProgress type="line" :percentage="task.progress" />
      <NDescriptions :column="2" style="margin-top: 20px">
        <NDescriptionsItem label="任务 ID">{{ task.id }}</NDescriptionsItem>
        <NDescriptionsItem label="项目 ID">{{ task.projectId }}</NDescriptionsItem>
        <NDescriptionsItem label="任务类型">{{ task.type }}</NDescriptionsItem>
        <NDescriptionsItem label="更新时间">{{ task.updatedAt }}</NDescriptionsItem>
      </NDescriptions>
    </NCard>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { NAlert, NCard, NDescriptions, NDescriptionsItem, NProgress, NSpin, NTag } from 'naive-ui'
import { useRoute } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { getModelTaskApi } from '@/api/workspace'
import type { ForgeTask } from '@/types/domain'

const route = useRoute()
const task = ref<ForgeTask | null>(null)
const loading = ref(false)
const errorMessage = ref('')

async function loadTask() {
  loading.value = true
  errorMessage.value = ''

  try {
    task.value = await getModelTaskApi(String(route.params.id))
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
