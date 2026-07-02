<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">OVERVIEW</p>
        <h1>工作台</h1>
        <p>项目、模型生成任务与切片任务的统一入口。</p>
      </div>
      <NButton type="primary" @click="router.push('/projects')">查看项目</NButton>
    </div>

    <div class="grid-3">
      <NCard title="项目数" :bordered="false"><NStatistic :value="dashboardStats.projects" /></NCard>
      <NCard title="运行中任务" :bordered="false"><NStatistic :value="dashboardStats.runningTasks" /></NCard>
      <NCard title="已完成任务" :bordered="false"><NStatistic :value="dashboardStats.completedTasks" /></NCard>
    </div>

    <NCard title="最近任务" :bordered="false">
      <NDataTable :columns="columns" :data="tasks" :pagination="false" />
    </NCard>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NButton, NCard, NDataTable, NProgress, NStatistic, NTag } from 'naive-ui'
import { h } from 'vue'
import { useRouter } from 'vue-router'

import { dashboardStats, tasks } from '@/mocks/workspace'
import type { ForgeTask } from '@/types/domain'

const router = useRouter()

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
</script>
