<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">SLICING</p>
        <h1>切片与 G-code</h1>
        <p>左侧检查模型与路径，右侧调整 OrcaSlicer 参数并生成 G-code。</p>
      </div>
      <NSpace>
        <NButton :disabled="!gcodeUrl" @click="downloadGcode">下载 G-code</NButton>
        <NButton type="primary" :loading="slicing" @click="createSlicingTask">开始切片</NButton>
      </NSpace>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />
    <NAlert v-if="successMessage" type="success" :title="successMessage" />

    <div class="slicer-workbench">
      <NCard :bordered="false" class="slicer-viewport-card">
        <template #header>
          <NSpace justify="space-between" align="center">
            <span>{{ project?.name ?? route.params.id }}</span>
            <NTag v-if="uploadedFile" round>{{ uploadedFile.filename }}</NTag>
          </NSpace>
        </template>
        <NTabs v-model:value="activePreview" type="line" animated>
          <NTabPane name="model" tab="模型">
            <ModelPreview
              :source-url="uploadedFile ? absoluteFileUrl(uploadedFile.fileUrl) : undefined"
              :filename="uploadedFile?.filename"
            />
          </NTabPane>
          <NTabPane name="toolpath" tab="切片路径">
            <GcodeLayerPreview :gcode-url="gcodeUrl || undefined" />
          </NTabPane>
        </NTabs>
      </NCard>

      <aside class="slicer-side-panel">
        <NCard title="材料与预设" :bordered="false">
          <NForm label-placement="top">
            <NFormItem label="切片模型">
              <NSelect v-model:value="selectedInputFilename" :options="savedFileOptions" />
            </NFormItem>
            <NFormItem label="Filament">
              <NSelect v-model:value="form.filamentType" :options="filamentOptions" />
            </NFormItem>
            <NFormItem label="Infill Pattern">
              <NSelect v-model:value="form.sparseInfillPattern" :options="infillOptions" />
            </NFormItem>
            <div class="slicing-form-grid">
              <NFormItem label="Nozzle Temp">
                <NInputNumber v-model:value="form.nozzleTemperature" :min="150" :max="320" />
              </NFormItem>
              <NFormItem label="Bed Temp">
                <NInputNumber v-model:value="form.bedTemperature" :min="0" :max="120" />
              </NFormItem>
            </div>
          </NForm>
        </NCard>

        <NCard title="质量与强度" :bordered="false">
          <NForm label-placement="top">
            <div class="slicing-form-grid">
              <NFormItem label="Layer Height">
                <NInputNumber v-model:value="form.layerHeight" :min="0.05" :max="0.6" :step="0.05" />
              </NFormItem>
              <NFormItem label="Line Width">
                <NInputNumber v-model:value="form.lineWidth" :min="0.2" :max="1.2" :step="0.05" />
              </NFormItem>
            </div>
            <div class="slicing-form-grid">
              <NFormItem label="Wall Loops">
                <NInputNumber v-model:value="form.wallLoops" :min="1" :max="8" />
              </NFormItem>
              <NFormItem label="Top / Bottom">
                <NSpace>
                  <NInputNumber v-model:value="form.topShellLayers" :min="0" :max="12" />
                  <NInputNumber v-model:value="form.bottomShellLayers" :min="0" :max="12" />
                </NSpace>
              </NFormItem>
            </div>
            <NFormItem label="Sparse Infill Density">
              <NSlider v-model:value="form.sparseInfillDensity" :min="0" :max="100" />
            </NFormItem>
          </NForm>
        </NCard>

        <NCard title="速度与附着" :bordered="false">
          <NForm label-placement="top">
            <NFormItem label="Print Speed">
              <NSlider v-model:value="form.speed" :min="10" :max="120" />
            </NFormItem>
            <NFormItem label="Travel Speed">
              <NSlider v-model:value="form.travelSpeed" :min="50" :max="300" />
            </NFormItem>
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

        <NCard v-if="project" title="输出" :bordered="false">
          <NDescriptions :column="1">
            <NDescriptionsItem label="Engine">OrcaSlicer</NDescriptionsItem>
            <NDescriptionsItem label="Firmware">Marlin</NDescriptionsItem>
            <NDescriptionsItem label="格式">.gcode</NDescriptionsItem>
            <NDescriptionsItem v-if="gcodeFilename" label="文件">{{ gcodeFilename }}</NDescriptionsItem>
          </NDescriptions>
        </NCard>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
  NTabPane,
  NTabs,
  NTag,
} from 'naive-ui'
import { useRoute } from 'vue-router'

import { loadAuthToken, normalizeApiError } from '@/api/client'
import {
  createSlicingTaskApi,
  getLatestProjectFileApi,
  getProjectApi,
  listProjectFilesApi,
  type UploadedFile,
} from '@/api/workspace'
import GcodeLayerPreview from '@/components/GcodeLayerPreview.vue'
import ModelPreview from '@/components/ModelPreview.vue'
import type { Project } from '@/types/domain'

const route = useRoute()
const project = ref<Project | null>(null)
const uploadedFile = ref<UploadedFile | null>(null)
const savedFiles = ref<UploadedFile[]>([])
const selectedInputFilename = ref<string | null>(null)
const errorMessage = ref('')
const successMessage = ref('')
const slicing = ref(false)
const activePreview = ref<'model' | 'toolpath'>('model')
const gcodeUrl = ref('')
const gcodeFilename = ref('')
const savedFileOptions = computed(() =>
  savedFiles.value.map((file) => ({
    label: `${file.filename} (${(file.sizeBytes / 1024 / 1024).toFixed(2)} MB)`,
    value: file.filename,
  })),
)
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
    const projectId = String(route.params.id)
    project.value = await getProjectApi(projectId)
    try {
      savedFiles.value = await listProjectFilesApi(projectId)
      uploadedFile.value = savedFiles.value[0] ?? (await getLatestProjectFileApi(projectId))
      selectedInputFilename.value = uploadedFile.value.filename
    } catch {
      uploadedFile.value = null
      savedFiles.value = []
      selectedInputFilename.value = null
    }
  } catch (error) {
    project.value = null
    uploadedFile.value = null
    errorMessage.value = normalizeApiError(error).message
  }
}

function absoluteFileUrl(fileUrl: string) {
  return `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}${fileUrl.replace('/api/v1', '')}`
}

async function createSlicingTask() {
  if (!selectedInputFilename.value) {
    errorMessage.value = '请先在模型上传页上传 STL/OBJ 文件'
    return
  }

  slicing.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const result = await createSlicingTaskApi(String(route.params.id), {
      inputFilename: selectedInputFilename.value,
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
    activePreview.value = 'toolpath'
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
watch(selectedInputFilename, (filename) => {
  uploadedFile.value = savedFiles.value.find((file) => file.filename === filename) ?? null
})
</script>
