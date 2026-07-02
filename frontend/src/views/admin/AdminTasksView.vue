<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">ADMIN TASKS</p>
        <h1>任务审计</h1>
        <p>统一查看模型生成、切片与 G-code 任务状态，后续支持重试和终止。</p>
      </div>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <NCard :bordered="false">
      <NDataTable :columns="columns" :data="tasks" :loading="loading" :pagination="false" />
    </NCard>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NAlert, NCard, NDataTable, NProgress, NTag } from 'naive-ui'
import { h, onMounted, ref } from 'vue'

import { normalizeApiError } from '@/api/client'
import { listAdminTasksApi } from '@/api/workspace'
import type { ForgeTask } from '@/types/domain'

const tasks = ref<ForgeTask[]>([])
const loading = ref(false)
const errorMessage = ref('')

const columns: DataTableColumns<ForgeTask> = [
  { title: '任务', key: 'name' },
  { title: '项目', key: 'projectId' },
  { title: '类型', key: 'type' },
  {
    title: '状态',
    key: 'status',
    render: (row) => h(NTag, { type: row.status === 'failed' ? 'error' : 'info' }, { default: () => row.status }),
  },
  { title: '进度', key: 'progress', render: (row) => h(NProgress, { percentage: row.progress, showIndicator: false }) },
]

async function loadTasks() {
  loading.value = true
  errorMessage.value = ''

  try {
    tasks.value = await listAdminTasksApi()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

onMounted(loadTasks)
</script>
