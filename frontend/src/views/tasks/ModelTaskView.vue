<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">MODEL TASK</p>
        <h1>{{ task.name }}</h1>
        <p>模型生成任务详情页，后续接入任务日志、预览文件和失败原因。</p>
      </div>
      <NTag :type="task.status === 'completed' ? 'success' : 'info'" round>{{ task.status }}</NTag>
    </div>

    <NCard :bordered="false">
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
import { computed } from 'vue'
import { NCard, NDescriptions, NDescriptionsItem, NProgress, NTag } from 'naive-ui'
import { useRoute } from 'vue-router'

import { findTask } from '@/mocks/workspace'

const route = useRoute()
const task = computed(() => findTask(String(route.params.id)))
</script>
