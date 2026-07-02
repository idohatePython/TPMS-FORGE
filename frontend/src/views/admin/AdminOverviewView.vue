<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">ADMIN</p>
        <h1>系统概览</h1>
        <p>管理员视角用于观察用户、项目、任务、文件与日志状态。</p>
      </div>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div class="grid-3">
      <NCard title="用户" :bordered="false"><NStatistic :value="summary.users" /></NCard>
      <NCard title="项目" :bordered="false"><NStatistic :value="summary.projects" /></NCard>
      <NCard title="任务" :bordered="false"><NStatistic :value="summary.tasks" /></NCard>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NAlert, NCard, NStatistic } from 'naive-ui'

import { normalizeApiError } from '@/api/client'
import { getAdminSummaryApi, type AdminSummary } from '@/api/workspace'

const summary = ref<AdminSummary>({ users: 0, projects: 0, tasks: 0 })
const errorMessage = ref('')

async function loadSummary() {
  errorMessage.value = ''

  try {
    summary.value = await getAdminSummaryApi()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

onMounted(loadSummary)
</script>
