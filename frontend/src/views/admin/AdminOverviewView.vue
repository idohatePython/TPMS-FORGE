<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">ADMIN</p>
        <h1>系统概览</h1>
        <p>管理员视角用于观察用户、项目、任务、文件与日志状态。</p>
      </div>
    </div>

    <div class="grid-3">
      <NCard title="用户" :bordered="false"><NStatistic :value="12" /></NCard>
      <NCard title="项目" :bordered="false"><NStatistic :value="dashboardStats.projects" /></NCard>
      <NCard title="任务" :bordered="false"><NStatistic :value="tasks.length" /></NCard>
    </div>
  </section>
</template>

<script setup lang="ts">
import { NCard, NStatistic } from 'naive-ui'

import { dashboardStats, tasks } from '@/mocks/workspace'
</script>
