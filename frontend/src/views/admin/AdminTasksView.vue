<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">ADMIN TASKS</p>
        <h1>任务审计</h1>
        <p>统一查看模型生成、切片与 G-code 任务状态，后续支持重试和终止。</p>
      </div>
    </div>

    <NCard :bordered="false">
      <NDataTable :columns="columns" :data="tasks" :pagination="false" />
    </NCard>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NCard, NDataTable, NProgress, NTag } from 'naive-ui'
import { h } from 'vue'

import { tasks } from '@/mocks/workspace'
import type { ForgeTask } from '@/types/domain'

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
</script>
