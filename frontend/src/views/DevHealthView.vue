<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getHealth, type HealthResponse } from '@/api/system'

const loading = ref(false)
const health = ref<HealthResponse | null>(null)
const error = ref('')

async function checkHealth() {
  loading.value = true
  error.value = ''

  try {
    health.value = await getHealth()
  } catch (err) {
    health.value = null
    error.value = err instanceof Error ? err.message : '无法连接后端服务'
  } finally {
    loading.value = false
  }
}

onMounted(checkHealth)
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <h2>后端健康检查</h2>
      <button type="button" @click="checkHealth">刷新</button>
    </div>

    <p v-if="loading">正在检查...</p>
    <p v-else-if="health" class="success">后端可用：{{ health.service }} / {{ health.status }}</p>
    <p v-else class="error">后端服务不可用：{{ error }}</p>
  </section>
</template>
