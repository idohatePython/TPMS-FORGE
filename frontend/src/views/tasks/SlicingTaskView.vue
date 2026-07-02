<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">SLICING TASK</p>
        <h1>{{ task.name }}</h1>
        <p>切片任务详情页，后续展示路径统计、G-code 下载与任务日志。</p>
      </div>
      <NButton :disabled="task.status !== 'completed'" type="primary">下载 G-code</NButton>
    </div>

    <div class="grid-2">
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
import { computed } from 'vue'
import { NButton, NCard, NDescriptions, NDescriptionsItem, NProgress } from 'naive-ui'
import { useRoute } from 'vue-router'

import { findTask } from '@/mocks/workspace'

const route = useRoute()
const task = computed(() => findTask(String(route.params.id)))
</script>
