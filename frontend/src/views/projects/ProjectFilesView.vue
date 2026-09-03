<template>
  <section class="page project-files-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">PROJECT FILES</p>
        <h1>模型与文件</h1>
        <p>选择当前模型，或查看项目中保留的 TPMS 模型和 G-code。</p>
      </div>
      <NSpace>
        <NButton @click="router.push(`/projects/${route.params.id}`)">返回项目</NButton>
        <NButton :loading="loading" @click="loadFiles">刷新</NButton>
      </NSpace>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />
    <NAlert v-if="successMessage" type="success" :title="successMessage" />

    <div class="project-files-grid">
      <section class="dashboard-panel project-files-current">
        <div class="dashboard-panel-heading">
          <div>
            <p class="eyebrow">CURRENT INPUT</p>
            <h2>当前模型</h2>
          </div>
          <NTag v-if="currentModel" type="success" round>已选择</NTag>
        </div>

        <ModelPreview
          class="project-files-model-preview"
          :source-url="currentModel ? absoluteFileUrl(currentModel.fileUrl) : undefined"
          :filename="currentModel?.filename"
          empty-description="选择模型文件后显示预览"
        />

        <div v-if="currentModel" class="project-file-meta">
          <div>
            <span>文件名</span>
            <strong>{{ currentModel.filename }}</strong>
          </div>
          <div>
            <span>大小</span>
            <strong>{{ formatFileSize(currentModel.sizeBytes) }}</strong>
          </div>
          <div>
            <span>来源</span>
            <strong>{{ fileKindLabel(currentModel) }}</strong>
          </div>
          <div>
            <span>存储</span>
            <strong>{{ currentModel.temporary ? '临时，任务成功后清理' : '项目持久保存' }}</strong>
          </div>
        </div>

        <NSpace>
          <NButton
            type="primary"
            :disabled="!currentModel"
            @click="router.push({ path: `/projects/${route.params.id}/slicing`, query: { infill: 'tpms' } })"
          >
            切片（TPMS）
          </NButton>
          <NButton :disabled="!currentModel" @click="router.push(`/projects/${route.params.id}/slicing`)">
            配置切片
          </NButton>
        </NSpace>
      </section>

      <section class="dashboard-panel">
        <div class="dashboard-panel-heading">
          <div>
            <p class="eyebrow">SUMMARY</p>
            <h2>文件统计</h2>
          </div>
          <NButton size="small" @click="router.push(`/projects/${route.params.id}/upload`)">上传模型</NButton>
        </div>

        <div class="project-file-summary">
          <div>
            <span>导入 / 生成</span>
            <strong>{{ uploadedModelFiles.length }} / {{ generatedModelFiles.length }}</strong>
          </div>
          <div>
            <span>G-code</span>
            <strong>{{ gcodeFiles.length }}</strong>
          </div>
          <div>
            <span>总大小</span>
            <strong>{{ formatFileSize(totalSizeBytes) }}</strong>
          </div>
        </div>
      </section>
    </div>

    <section class="dashboard-panel project-file-library">
      <div class="dashboard-panel-heading">
        <div>
          <p class="eyebrow">IMPORTED MODELS</p>
          <h2>导入模型</h2>
        </div>
        <NTag round>{{ uploadedModelFiles.length }} 个</NTag>
      </div>
      <div v-if="uploadedModelFiles.length" class="project-file-card-grid">
        <article
          v-for="file in uploadedModelFiles"
          :key="file.filename"
          class="project-file-card"
          :class="{ 'is-current': file.filename === currentModel?.filename }"
        >
          <div class="project-file-card-icon">STL</div>
          <div class="project-file-card-copy">
            <NSpace align="center" size="small">
              <strong>{{ file.filename }}</strong>
              <NTag v-if="file.filename === currentModel?.filename" type="success" size="small" round>当前</NTag>
              <NTag type="warning" size="small" round>临时</NTag>
            </NSpace>
            <span>{{ formatFileSize(file.sizeBytes) }} · {{ formatCreatedAt(file.createdAt) }}</span>
            <small>任务成功后自动清理</small>
          </div>
          <NSpace class="project-file-card-actions" size="small">
            <NButton size="small" @click="previewModel(file)">预览</NButton>
            <NButton v-if="file.filename !== currentModel?.filename" size="small" type="primary" secondary @click="selectModel(file)">设为当前</NButton>
            <NPopconfirm @positive-click="deleteFile(file, 'model')">
              <template #trigger><NButton size="small" quaternary type="error">删除</NButton></template>
              确定删除 {{ file.filename }}？
            </NPopconfirm>
          </NSpace>
        </article>
      </div>
      <NEmpty v-else description="尚未上传 STL 或 OBJ 模型" />
    </section>

    <section class="dashboard-panel project-file-library">
      <div class="dashboard-panel-heading">
        <div>
          <p class="eyebrow">GENERATED MODELS</p>
          <h2>TPMS 生成模型</h2>
        </div>
        <NTag round>{{ generatedModelFiles.length }} 个</NTag>
      </div>
      <div v-if="generatedModelFiles.length" class="project-file-card-grid">
        <article
          v-for="file in generatedModelFiles"
          :key="file.filename"
          class="project-file-card"
          :class="{ 'is-current': file.filename === currentModel?.filename }"
        >
          <div class="project-file-card-icon is-generated">TPMS</div>
          <div class="project-file-card-copy">
            <NSpace align="center" size="small">
              <strong>{{ file.filename }}</strong>
              <NTag v-if="file.filename === currentModel?.filename" type="success" size="small" round>当前</NTag>
              <NTag type="info" size="small" round>持久</NTag>
            </NSpace>
            <span>{{ formatFileSize(file.sizeBytes) }} · {{ formatCreatedAt(file.createdAt) }}</span>
            <small>{{ file.sourceTaskId ? `由任务 ${file.sourceTaskId} 生成` : '平台生成模型' }}</small>
          </div>
          <NSpace class="project-file-card-actions" size="small">
            <NButton size="small" @click="previewModel(file)">预览</NButton>
            <NButton v-if="file.filename !== currentModel?.filename" size="small" type="primary" secondary @click="selectModel(file)">设为当前</NButton>
            <NButton size="small" @click="openSlicing(file)">切片</NButton>
            <NButton size="small" quaternary @click="downloadFile(file)">下载</NButton>
            <NPopconfirm @positive-click="deleteFile(file, 'model')">
              <template #trigger><NButton size="small" quaternary type="error">删除</NButton></template>
              确定删除 {{ file.filename }}？
            </NPopconfirm>
          </NSpace>
        </article>
      </div>
      <NEmpty v-else description="尚未生成 TPMS STL 模型" />
    </section>

    <section class="dashboard-panel project-file-library">
      <div class="dashboard-panel-heading">
        <div>
          <p class="eyebrow">G-CODE OUTPUTS</p>
          <h2>切片输出</h2>
        </div>
        <NTag round>{{ gcodeFiles.length }} 个</NTag>
      </div>
      <div v-if="gcodeFiles.length" class="project-file-card-grid">
        <article v-for="file in gcodeFiles" :key="file.filename" class="project-file-card">
          <div class="project-file-card-icon is-gcode">G</div>
          <div class="project-file-card-copy">
            <NSpace align="center" size="small">
              <strong>{{ file.filename }}</strong>
              <NTag type="info" size="small" round>持久</NTag>
            </NSpace>
            <span>{{ formatFileSize(file.sizeBytes) }} · {{ formatCreatedAt(file.createdAt) }}</span>
            <small>{{ file.sourceTaskId ? `由任务 ${file.sourceTaskId} 生成` : 'G-code 切片输出' }}</small>
          </div>
          <NSpace class="project-file-card-actions" size="small">
            <NButton size="small" type="primary" secondary @click="downloadFile(file)">下载 G-code</NButton>
            <NPopconfirm @positive-click="deleteFile(file, 'gcode')">
              <template #trigger><NButton size="small" quaternary type="error">删除</NButton></template>
              确定删除 {{ file.filename }}？
            </NPopconfirm>
          </NSpace>
        </article>
      </div>
      <NEmpty v-else description="尚未生成 G-code" />
    </section>
  </section>
</template>

<script setup lang="ts">
import {
  NAlert,
  NButton,
  NEmpty,
  NPopconfirm,
  NSpace,
  NTag,
} from 'naive-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { loadAuthToken, normalizeApiError } from '@/api/client'
import {
  deleteProjectFileApi,
  deleteProjectGcodeFileApi,
  getLatestProjectFileApi,
  listProjectFilesApi,
  listProjectGcodeFilesApi,
  selectLatestProjectFileApi,
  type UploadedFile,
} from '@/api/workspace'
import ModelPreview from '@/components/ModelPreview.vue'

const route = useRoute()
const router = useRouter()
const modelFiles = ref<UploadedFile[]>([])
const gcodeFiles = ref<UploadedFile[]>([])
const currentModel = ref<UploadedFile | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const uploadedModelFiles = computed(() => modelFiles.value.filter((file) => file.fileKind === 'uploaded_model'))
const generatedModelFiles = computed(() => modelFiles.value.filter((file) => file.fileKind === 'generated_model'))

const totalSizeBytes = computed(() =>
  [...modelFiles.value, ...gcodeFiles.value].reduce((total, file) => total + file.sizeBytes, 0),
)

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`
  return `${(sizeBytes / 1024 / 1024).toFixed(2)} MB`
}

function formatCreatedAt(createdAt: string) {
  return createdAt.replace('T', ' ')
}

function fileKindLabel(file: UploadedFile) {
  if (file.fileKind === 'generated_model') return 'TPMS 生成模型'
  if (file.fileKind === 'gcode') return '切片输出'
  return '本地导入模型'
}

function absoluteFileUrl(fileUrl: string) {
  return `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}${fileUrl.replace('/api/v1', '')}`
}

async function loadFiles() {
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const projectId = String(route.params.id)
    const [models, gcodes] = await Promise.all([
      listProjectFilesApi(projectId),
      listProjectGcodeFilesApi(projectId),
    ])
    modelFiles.value = models
    gcodeFiles.value = gcodes
    try {
      currentModel.value = await getLatestProjectFileApi(projectId)
    } catch {
      currentModel.value = models[0] ?? null
    }
  } catch (error) {
    modelFiles.value = []
    gcodeFiles.value = []
    currentModel.value = null
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

async function selectModel(file: UploadedFile) {
  try {
    currentModel.value = await selectLatestProjectFileApi(String(route.params.id), file.filename)
    await loadFiles()
    successMessage.value = `${file.filename} 已设为当前输入`
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

function previewModel(file: UploadedFile) {
  currentModel.value = file
  document.querySelector('.project-files-current')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function openSlicing(file: UploadedFile) {
  if (file.filename !== currentModel.value?.filename) await selectModel(file)
  await router.push(`/projects/${route.params.id}/slicing`)
}

async function downloadFile(file: UploadedFile) {
  try {
    const response = await fetch(absoluteFileUrl(file.fileUrl), {
      headers: { Authorization: `Bearer ${loadAuthToken()}` },
    })
    if (!response.ok) throw new Error(`文件下载失败：${response.status}`)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.filename
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '文件下载失败'
  }
}

async function deleteFile(file: UploadedFile, kind: 'model' | 'gcode') {
  try {
    const projectId = String(route.params.id)
    if (kind === 'model') await deleteProjectFileApi(projectId, file.filename)
    else await deleteProjectGcodeFileApi(projectId, file.filename)
    await loadFiles()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

onMounted(loadFiles)
watch(() => route.params.id, loadFiles)
</script>
