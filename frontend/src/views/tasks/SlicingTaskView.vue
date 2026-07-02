<template>
  <section class="page">
    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div v-if="task" class="page-heading">
      <div>
        <p class="eyebrow">SLICING TASK</p>
        <h1>{{ task.name }}</h1>
        <p>切片任务详情页，后续展示路径统计、G-code 下载与任务日志。</p>
      </div>
      <NButton :disabled="task.status !== 'completed'" type="primary">下载 G-code</NButton>
    </div>

    <NSpin v-if="loading" size="large" />

    <div v-if="task" class="grid-2">
      <NCard title="任务进度" :bordered="false">
        <NProgress type="dashboard" :percentage="task.progress" />
      </NCard>
      <NCard title="输出摘要" :bordered="false">
        <NDescriptions :column="1">
          <NDescriptionsItem label="Firmware">Marlin</NDescriptionsItem>
          <NDescriptionsItem label="预计文件">output_{{ task.id }}.gcode</NDescriptionsItem>
          <NDescriptionsItem label="更新时间">{{ task.updatedAt }}</NDescriptionsItem>
        </NDescriptions>
      </NCard>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { NAlert, NButton, NCard, NDescriptions, NDescriptionsItem, NProgress, NSpin } from 'naive-ui'
import { useRoute } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { getSlicingTaskApi } from '@/api/workspace'
import type { ForgeTask } from '@/types/domain'

const route = useRoute()
const task = ref<ForgeTask | null>(null)
const loading = ref(false)
const errorMessage = ref('')

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
