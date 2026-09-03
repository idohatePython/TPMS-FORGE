<template>
  <section class="page project-upload-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">UPLOAD</p>
        <h1>模型导入</h1>
        <p>{{ project?.name ?? route.params.id }} 的模型会作为当前输入保存在项目中；已有模型无需重复上传。</p>
      </div>
      <NSpace>
        <NButton @click="router.push(`/projects/${route.params.id}`)">返回项目</NButton>
        <NButton :loading="loading" @click="loadProject">刷新</NButton>
      </NSpace>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />
    <NAlert v-if="successMessage" type="success" :title="successMessage" />

    <div class="project-upload-grid">
      <section class="dashboard-panel project-upload-panel">
        <div class="dashboard-panel-heading">
          <div>
            <p class="eyebrow">MODEL INPUT</p>
            <h2>{{ uploadedFile ? '当前模型' : '导入 STL / OBJ' }}</h2>
          </div>
          <NTag v-if="uploadedFile" type="success" round>当前输入</NTag>
        </div>

        <NUpload
          directory-dnd
          :max="1"
          accept=".stl,.obj"
          :show-file-list="false"
          :custom-request="uploadFile"
          @before-upload="beforeUpload"
        >
          <NUploadDragger class="project-upload-dragger">
            <div class="project-upload-copy">
              <strong>{{ uploadedFile ? '更换模型文件' : '拖入或点击选择模型文件' }}</strong>
              <span>{{ uploadedFile ? '已有模型会继续保留；只有选择新文件时才需要上传。' : '支持 STL / OBJ，上传后会自动设为当前输入文件。' }}</span>
            </div>
          </NUploadDragger>
        </NUpload>

        <div class="project-upload-rules">
          <div>
            <span>格式</span>
            <strong>STL / OBJ</strong>
          </div>
          <div>
            <span>状态</span>
            <strong>{{ uploadedFile ? '已选择输入' : '等待上传' }}</strong>
          </div>
          <div>
            <span>当前文件</span>
            <strong>{{ uploadedFile?.filename ?? '无' }}</strong>
          </div>
          <div>
            <span>存储方式</span>
            <strong>{{ uploadedFile ? (uploadedFile.temporary ? '临时文件 · 任务成功后自动清理' : '项目文件 · 持久保存') : '等待导入' }}</strong>
          </div>
        </div>

        <NSpace class="project-upload-actions">
          <NButton
            :disabled="!uploadedFile"
            type="primary"
            @click="goToDirectSlicing"
          >
            直接切片原始模型
          </NButton>
          <NButton
            :disabled="!uploadedFile"
            secondary
            @click="router.push({ path: `/projects/${route.params.id}/slicing`, query: { infill: 'tpms' } })"
          >
            TPMS 填充后切片
          </NButton>
        </NSpace>
        <p class="project-upload-action-note">直接切片默认使用普通填充；进入切片工作区后仍可随时切换为 TPMS 梯度填充。</p>
      </section>

      <section class="project-upload-preview">
        <ModelPreview
          :source-url="uploadedFile ? absoluteFileUrl(uploadedFile.fileUrl) : undefined"
          :filename="uploadedFile?.filename"
          :bed-size="previewBedSize"
          empty-description="上传或选择模型后显示预览"
        />
      </section>
    </div>

    <section class="dashboard-panel project-file-picker">
      <div class="dashboard-panel-heading">
        <div>
          <p class="eyebrow">SAVED MODELS</p>
          <h2>项目已有模型</h2>
        </div>
        <NTag round>{{ savedFiles.length }} 个</NTag>
      </div>

      <NDataTable
        v-if="savedFiles.length"
        :columns="columns"
        :data="savedFiles"
        :pagination="false"
        :bordered="false"
      />
      <NEmpty v-else description="尚未上传 STL 或 OBJ 模型" />
    </section>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns, UploadCustomRequestOptions, UploadFileInfo } from 'naive-ui'
import {
  NAlert,
  NButton,
  NDataTable,
  NEmpty,
  NSpace,
  NTag,
  NUpload,
  NUploadDragger,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import ModelPreview from '@/components/ModelPreview.vue'
import {
  getProjectApi,
  getLatestProjectFileApi,
  listProjectFilesApi,
  selectLatestProjectFileApi,
  uploadProjectFileApi,
  type UploadedFile,
} from '@/api/workspace'
import type { Project } from '@/types/domain'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const uploadedFile = ref<UploadedFile | null>(null)
const savedFiles = ref<UploadedFile[]>([])
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const previewBedSize = computed(() => 250)

const columns: DataTableColumns<UploadedFile> = [
  {
    title: '文件名',
    key: 'filename',
    render: (file) =>
      h('span', { class: file.filename === uploadedFile.value?.filename ? 'project-current-file' : '' }, file.filename),
  },
  { title: '大小', key: 'sizeBytes', width: 130, render: (file) => formatFileSize(file.sizeBytes) },
  {
    title: '来源',
    key: 'fileKind',
    width: 120,
    render: (file) => file.fileKind === 'generated_model' ? '平台生成' : '本地导入',
  },
  {
    title: '存储',
    key: 'temporary',
    width: 110,
    render: (file) => file.temporary ? '临时' : '永久',
  },
  {
    title: '当前输入',
    key: 'selected',
    width: 120,
    render: (file) =>
      file.filename === uploadedFile.value?.filename
        ? h(NTag, { type: 'success', round: true }, { default: () => '已选择' })
        : h(NButton, { size: 'small', onClick: () => void selectSavedFile(file.filename) }, { default: () => '设为当前' }),
  },
]

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`
  return `${(sizeBytes / 1024 / 1024).toFixed(2)} MB`
}

function absoluteFileUrl(fileUrl: string) {
  return `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}${fileUrl.replace('/api/v1', '')}`
}

function beforeUpload(data: { file: UploadFileInfo }) {
  const filename = data.file.name
  const suffix = filename.split('.').pop()?.toLowerCase()
  if (!suffix || !['stl', 'obj'].includes(suffix)) {
    errorMessage.value = '仅支持 STL 或 OBJ 文件'
    return false
  }
  return true
}

async function refreshFiles(projectId: string) {
  savedFiles.value = await listProjectFilesApi(projectId)
  try {
    uploadedFile.value = await getLatestProjectFileApi(projectId)
  } catch {
    uploadedFile.value = savedFiles.value[0] ?? null
  }
}

async function loadProject() {
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const projectId = String(route.params.id)
    project.value = await getProjectApi(projectId)
    await refreshFiles(projectId)
  } catch (error) {
    project.value = null
    uploadedFile.value = null
    savedFiles.value = []
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

async function uploadFile(options: UploadCustomRequestOptions) {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const rawFile = options.file.file
    if (!rawFile) {
      throw new Error('请选择有效文件')
    }

    uploadedFile.value = await uploadProjectFileApi(String(route.params.id), rawFile)
    await refreshFiles(String(route.params.id))
    successMessage.value = `${uploadedFile.value.filename} 已保存为当前输入`
    options.onFinish()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    options.onError()
  }
}

async function selectSavedFile(filename: string): Promise<boolean> {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    uploadedFile.value = await selectLatestProjectFileApi(String(route.params.id), filename)
    await refreshFiles(String(route.params.id))
    successMessage.value = `${filename} 已设为当前输入`
    return true
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    return false
  }
}

async function goToDirectSlicing() {
  const originalModel = savedFiles.value.find((file) => file.fileKind === 'uploaded_model')
  if (originalModel && originalModel.filename !== uploadedFile.value?.filename) {
    const selected = await selectSavedFile(originalModel.filename)
    if (!selected) return
  }
  if (!uploadedFile.value) return
  await router.push(`/projects/${route.params.id}/slicing`)
}

onMounted(loadProject)
watch(() => route.params.id, loadProject)
</script>
