<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">TPMS GENERATION</p>
        <h1>TPMS 生成</h1>
        <p>面向项目 {{ project?.name ?? route.params.id }} 的结构生成参数页，后续提交 Celery 模型生成任务。</p>
      </div>
      <NButton type="primary" @click="router.push('/model-tasks/mg-2048')">查看任务</NButton>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div class="grid-2">
      <NCard title="生成参数" :bordered="false">
        <NForm label-placement="top">
          <NFormItem label="TPMS 类型">
            <NSelect v-model:value="form.type" :options="typeOptions" />
          </NFormItem>
          <NFormItem label="Cell Size">
            <NSlider v-model:value="form.cellSize" :min="2" :max="24" />
          </NFormItem>
          <NFormItem label="Boundary Mode">
            <NRadioGroup v-model:value="form.boundary">
              <NRadioButton v-for="option in boundaryOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </NRadioButton>
            </NRadioGroup>
          </NFormItem>
        </NForm>
      </NCard>
      <div class="preview-panel">
        <div class="tpms-lattice" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { NAlert, NButton, NCard, NForm, NFormItem, NRadioButton, NRadioGroup, NSelect, NSlider } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { getProjectApi } from '@/api/workspace'
import type { Project } from '@/types/domain'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const errorMessage = ref('')
const form = reactive({ type: 'Gyroid', cellSize: 8, boundary: 'model' })
const typeOptions = ['Schwarz-P', 'Gyroid', 'Diamond'].map((value) => ({ label: value, value }))
const boundaryOptions = [
  { label: '模型边界', value: 'model' },
  { label: '规则包围盒', value: 'box' },
]

async function loadProject() {
  errorMessage.value = ''

  try {
    project.value = await getProjectApi(String(route.params.id))
  } catch (error) {
    project.value = null
    errorMessage.value = normalizeApiError(error).message
  }
}

onMounted(loadProject)
watch(() => route.params.id, loadProject)
</script>
