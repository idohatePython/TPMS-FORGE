<template>
  <main class="section">
    <div class="section-inner page">
      <div class="page-heading">
        <div>
          <p class="eyebrow">DEV HEALTH</p>
          <h1>开发环境健康检查</h1>
          <p>用于验证前端到后端 `/health` 接口的连通性。</p>
        </div>
        <NButton type="primary" :loading="loading" @click="loadHealth">
          {{ hasChecked ? '重新检查' : '开始检查' }}
        </NButton>
      </div>

      <NCard :bordered="false">
        <NDescriptions v-if="health" :column="1">
          <NDescriptionsItem label="Status">{{ health.status }}</NDescriptionsItem>
          <NDescriptionsItem label="Service">{{ health.service }}</NDescriptionsItem>
          <NDescriptionsItem label="检查时间">{{ checkedAt }}</NDescriptionsItem>
        </NDescriptions>
        <NAlert v-else-if="error" type="error" :title="error.message" />
        <NEmpty v-else description="尚未检查，点击“开始检查”验证服务状态" />
      </NCard>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NAlert, NButton, NCard, NDescriptions, NDescriptionsItem, NEmpty } from 'naive-ui'

import { normalizeApiError, type ApiError } from '@/api/client'
import { getHealth, type HealthResponse } from '@/api/system'

const health = ref<HealthResponse | null>(null)
const error = ref<ApiError | null>(null)
const loading = ref(false)
const checkedAt = ref('')
const hasChecked = computed(() => health.value !== null || error.value !== null)

async function loadHealth() {
  loading.value = true
  error.value = null

  try {
    health.value = await getHealth()
  } catch (caught) {
    health.value = null
    error.value = normalizeApiError(caught)
  } finally {
    checkedAt.value = new Date().toLocaleString('zh-CN')
    loading.value = false
  }
}
</script>
