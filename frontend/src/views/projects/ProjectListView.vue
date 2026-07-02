<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">PROJECTS</p>
        <h1>项目管理</h1>
        <p>项目是原始模型、TPMS 生成任务、切片任务、日志与下载结果的业务容器。</p>
      </div>
      <NButton type="primary">新建项目</NButton>
    </div>

    <NCard :bordered="false">
      <NDataTable :columns="columns" :data="projects" :pagination="false" />
    </NCard>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NButton, NCard, NDataTable, NTag } from 'naive-ui'
import { h } from 'vue'
import { RouterLink } from 'vue-router'

import { projects } from '@/mocks/workspace'
import type { Project } from '@/types/domain'

const columns: DataTableColumns<Project> = [
  {
    title: '项目名称',
    key: 'name',
    render: (row) => h(RouterLink, { to: `/projects/${row.id}` }, { default: () => row.name }),
  },
  { title: '模型文件', key: 'modelFile' },
  { title: '材料', key: 'material' },
  {
    title: '状态',
    key: 'status',
    render: (row) => h(NTag, { type: row.status === 'completed' ? 'success' : 'info' }, { default: () => row.status }),
  },
  { title: '更新时间', key: 'updatedAt' },
]
</script>
