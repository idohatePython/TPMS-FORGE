<template>
  <main class="section">
    <div class="section-inner page">
      <div class="page-heading">
        <div>
          <p class="eyebrow">DEV HEALTH</p>
          <h1>开发环境健康检查</h1>
          <p>用于验证前端到后端 `/health` 接口的连通性。</p>
        </div>
        <NButton type="primary" :loading="loading" @click="loadHealth">刷新</NButton>
      </div>

      <NCard :bordered="false">
        <NDescriptions v-if="health" :column="1">
          <NDescriptionsItem label="Status">{{ health.status }}</NDescriptionsItem>
          <NDescriptionsItem label="Service">{{ health.service }}</NDescriptionsItem>
        </NDescriptions>
        <NAlert v-else-if="error" type="error" :title="error.message" />
        <NEmpty v-else description="尚未获取健康检查结果" />
      </NCard>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NAlert, NButton, NCard, NDescriptions, NDescriptionsItem, NEmpty } from 'naive-ui'

import { normalizeApiError, type ApiError } from '@/api/client'
import { getHealth, type HealthResponse } from '@/api/system'

const health = ref<HealthResponse | null>(null)
const error = ref<ApiError | null>(null)
const loading = ref(false)

async function loadHealth() {
  loading.value = true
  error.value = null

  try {
    health.value = await getHealth()
  } catch (caught) {
    health.value = null
    error.value = normalizeApiError(caught)
  } finally {
    loading.value = false
  }
}

onMounted(loadHealth)
</script>
