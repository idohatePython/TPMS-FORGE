<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">SLICING</p>
        <h1>切片与 G-code</h1>
        <p>配置 {{ project?.name ?? route.params.id }} 的层高、线宽、速度等参数，后续提交切片与 G-code 生成任务。</p>
      </div>
      <NButton type="primary" @click="router.push('/slicing-tasks/sg-1024')">查看切片任务</NButton>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div class="grid-2">
      <NCard title="切片参数" :bordered="false">
        <NForm label-placement="top">
          <NFormItem label="Layer Height">
            <NInputNumber v-model:value="form.layerHeight" :min="0.05" :max="0.6" :step="0.05" />
          </NFormItem>
          <NFormItem label="Line Width">
            <NInputNumber v-model:value="form.lineWidth" :min="0.2" :max="1.2" :step="0.05" />
          </NFormItem>
          <NFormItem label="Print Speed">
            <NSlider v-model:value="form.speed" :min="10" :max="120" />
          </NFormItem>
        </NForm>
      </NCard>
      <NCard v-if="project" title="输出目标" :bordered="false">
        <NDescriptions :column="1">
          <NDescriptionsItem label="Firmware">Marlin</NDescriptionsItem>
          <NDescriptionsItem label="格式">.gcode</NDescriptionsItem>
          <NDescriptionsItem label="项目">{{ project.name }}</NDescriptionsItem>
        </NDescriptions>
      </NCard>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { NAlert, NButton, NCard, NDescriptions, NDescriptionsItem, NForm, NFormItem, NInputNumber, NSlider } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { getProjectApi } from '@/api/workspace'
import type { Project } from '@/types/domain'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const errorMessage = ref('')
const form = reactive({ layerHeight: 0.2, lineWidth: 0.42, speed: 60 })

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
