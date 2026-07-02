<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">SLICING</p>
        <h1>切片与 G-code</h1>
        <p>配置 {{ project?.name ?? route.params.id }} 的层高、线宽、速度等参数，后续提交切片与 G-code 生成任务。</p>
      </div>
      <NButton type="primary" :loading="slicing" @click="createSlicingTask">开始切片</NButton>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />
    <NAlert v-if="successMessage" type="success" :title="successMessage" />

    <div class="grid-2">
      <NCard title="切片参数" :bordered="false">
        <NForm label-placement="top">
          <div class="slicing-form-grid">
            <NFormItem label="Filament">
              <NSelect v-model:value="form.filamentType" :options="filamentOptions" />
            </NFormItem>
            <NFormItem label="Infill Pattern">
              <NSelect v-model:value="form.sparseInfillPattern" :options="infillOptions" />
            </NFormItem>
          </div>
          <NFormItem label="Layer Height">
            <NInputNumber v-model:value="form.layerHeight" :min="0.05" :max="0.6" :step="0.05" />
          </NFormItem>
          <NFormItem label="Line Width">
            <NInputNumber v-model:value="form.lineWidth" :min="0.2" :max="1.2" :step="0.05" />
          </NFormItem>
          <div class="slicing-form-grid">
            <NFormItem label="Wall Loops">
              <NInputNumber v-model:value="form.wallLoops" :min="1" :max="8" />
            </NFormItem>
            <NFormItem label="Top / Bottom Layers">
              <NSpace>
                <NInputNumber v-model:value="form.topShellLayers" :min="0" :max="12" />
                <NInputNumber v-model:value="form.bottomShellLayers" :min="0" :max="12" />
              </NSpace>
            </NFormItem>
          </div>
          <NFormItem label="Sparse Infill Density">
            <NSlider v-model:value="form.sparseInfillDensity" :min="0" :max="100" />
          </NFormItem>
          <NFormItem label="Print Speed">
            <NSlider v-model:value="form.speed" :min="10" :max="120" />
          </NFormItem>
          <NFormItem label="Travel Speed">
            <NSlider v-model:value="form.travelSpeed" :min="50" :max="300" />
          </NFormItem>
          <div class="slicing-form-grid">
            <NFormItem label="Nozzle Temperature">
              <NInputNumber v-model:value="form.nozzleTemperature" :min="150" :max="320" />
            </NFormItem>
            <NFormItem label="Bed Temperature">
              <NInputNumber v-model:value="form.bedTemperature" :min="0" :max="120" />
            </NFormItem>
          </div>
          <div class="slicing-form-grid">
            <NFormItem label="Support">
              <NSwitch v-model:value="form.enableSupport" />
            </NFormItem>
            <NFormItem label="Brim Width">
              <NInputNumber v-model:value="form.brimWidth" :min="0" :max="20" :step="0.5" />
            </NFormItem>
          </div>
        </NForm>
      </NCard>
      <NCard v-if="project" title="输出目标" :bordered="false">
        <NDescriptions :column="1">
          <NDescriptionsItem label="Firmware">Marlin</NDescriptionsItem>
          <NDescriptionsItem label="格式">.gcode</NDescriptionsItem>
          <NDescriptionsItem label="项目">{{ project.name }}</NDescriptionsItem>
          <NDescriptionsItem v-if="gcodeUrl" label="G-code">
            <NButton text type="primary" @click="downloadGcode">下载 {{ gcodeFilename }}</NButton>
          </NDescriptionsItem>
        </NDescriptions>
      </NCard>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NForm,
  NFormItem,
  NInputNumber,
  NSelect,
  NSlider,
  NSpace,
  NSwitch,
} from 'naive-ui'
import { useRoute } from 'vue-router'

import { loadAuthToken, normalizeApiError } from '@/api/client'
import { createSlicingTaskApi, getProjectApi } from '@/api/workspace'
import type { Project } from '@/types/domain'

const route = useRoute()
const project = ref<Project | null>(null)
const errorMessage = ref('')
const successMessage = ref('')
const slicing = ref(false)
const gcodeUrl = ref('')
const gcodeFilename = ref('')
const form = reactive({
  layerHeight: 0.2,
  lineWidth: 0.42,
  speed: 60,
  travelSpeed: 150,
  wallLoops: 2,
  topShellLayers: 4,
  bottomShellLayers: 3,
  sparseInfillDensity: 15,
  sparseInfillPattern: 'gyroid',
  enableSupport: false,
  supportType: 'normal(auto)',
  brimWidth: 0,
  nozzleTemperature: 220,
  bedTemperature: 60,
  filamentType: 'PLA',
})

const filamentOptions = ['PLA', 'PETG', 'ABS', 'ASA', 'TPU', 'PA-CF'].map((value) => ({
  label: value,
  value,
}))
const infillOptions = ['gyroid', 'grid', 'honeycomb', 'cubic', 'rectilinear', 'triangles'].map(
  (value) => ({ label: value, value }),
)

async function loadProject() {
  errorMessage.value = ''

  try {
    project.value = await getProjectApi(String(route.params.id))
  } catch (error) {
    project.value = null
    errorMessage.value = normalizeApiError(error).message
  }
}

function absoluteFileUrl(fileUrl: string) {
  return `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}${fileUrl.replace('/api/v1', '')}`
}

async function createSlicingTask() {
  slicing.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const result = await createSlicingTaskApi(String(route.params.id), {
      layerHeight: form.layerHeight,
      lineWidth: form.lineWidth,
      printSpeed: form.speed,
      travelSpeed: form.travelSpeed,
      wallLoops: form.wallLoops,
      topShellLayers: form.topShellLayers,
      bottomShellLayers: form.bottomShellLayers,
      sparseInfillDensity: form.sparseInfillDensity,
      sparseInfillPattern: form.sparseInfillPattern,
      enableSupport: form.enableSupport,
      supportType: form.supportType,
      brimWidth: form.brimWidth,
      nozzleTemperature: form.nozzleTemperature,
      bedTemperature: form.bedTemperature,
      filamentType: form.filamentType,
    })
    gcodeUrl.value = absoluteFileUrl(result.gcodeUrl)
    gcodeFilename.value = result.gcodeFilename
    successMessage.value = `切片完成：${result.gcodeFilename}`
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    slicing.value = false
  }
}

function downloadGcode() {
  fetch(gcodeUrl.value, {
    headers: { Authorization: `Bearer ${loadAuthToken()}` },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`G-code 下载失败：${response.status}`)
      }
      return response.blob()
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = gcodeFilename.value || 'output.gcode'
      link.click()
      URL.revokeObjectURL(url)
    })
    .catch((error: unknown) => {
      errorMessage.value = error instanceof Error ? error.message : 'G-code 下载失败'
    })
}

onMounted(loadProject)
watch(() => route.params.id, loadProject)
</script>
