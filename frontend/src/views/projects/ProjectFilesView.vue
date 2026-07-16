<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">PROJECT FILES</p>
        <h1>项目文件</h1>
        <p>模型与切片结果保存在项目外的数据目录中，不会进入 Git 仓库。</p>
      </div>
      <NButton :loading="loading" @click="loadFiles">刷新</NButton>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <NCard title="模型文件" :bordered="false">
      <NDataTable v-if="modelFiles.length" :columns="modelColumns" :data="modelFiles" :bordered="false" />
      <NEmpty v-else description="尚未上传 STL 或 OBJ 模型" />
    </NCard>

    <NCard title="G-code 文件" :bordered="false">
      <NDataTable v-if="gcodeFiles.length" :columns="gcodeColumns" :data="gcodeFiles" :bordered="false" />
      <NEmpty v-else description="尚未生成 G-code" />
    </NCard>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NAlert, NButton, NCard, NDataTable, NEmpty, NPopconfirm, NSpace } from 'naive-ui'
import { h, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { loadAuthToken, normalizeApiError } from '@/api/client'
import {
  deleteProjectFileApi,
  deleteProjectGcodeFileApi,
  listProjectFilesApi,
  listProjectGcodeFilesApi,
  type UploadedFile,
} from '@/api/workspace'

const route = useRoute()
const modelFiles = ref<UploadedFile[]>([])
const gcodeFiles = ref<UploadedFile[]>([])
const loading = ref(false)
const errorMessage = ref('')

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`
  return `${(sizeBytes / 1024 / 1024).toFixed(2)} MB`
}

function absoluteFileUrl(fileUrl: string) {
  return `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}${fileUrl.replace('/api/v1', '')}`
}

async function loadFiles() {
  loading.value = true
  errorMessage.value = ''
  try {
    const projectId = String(route.params.id)
    const [models, gcodes] = await Promise.all([
      listProjectFilesApi(projectId),
      listProjectGcodeFilesApi(projectId),
    ])
    modelFiles.value = models
    gcodeFiles.value = gcodes
  } catch (error) {
    modelFiles.value = []
    gcodeFiles.value = []
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
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

function actionColumn(kind: 'model' | 'gcode') {
  return {
    title: '操作',
    key: 'actions',
    width: 168,
    render: (file: UploadedFile) =>
      h(NSpace, { size: 8 }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => void downloadFile(file) }, { default: () => '下载' }),
          h(
            NPopconfirm,
            { onPositiveClick: () => void deleteFile(file, kind) },
            {
              default: () => `确定删除 ${file.filename}？此操作不可恢复。`,
              trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
            },
          ),
        ],
      }),
  }
}

const baseColumns: DataTableColumns<UploadedFile> = [
  { title: '文件名', key: 'filename' },
  { title: '大小', key: 'sizeBytes', width: 130, render: (file) => formatFileSize(file.sizeBytes) },
]
const modelColumns: DataTableColumns<UploadedFile> = [...baseColumns, actionColumn('model')]
const gcodeColumns: DataTableColumns<UploadedFile> = [...baseColumns, actionColumn('gcode')]

onMounted(loadFiles)
watch(() => route.params.id, loadFiles)
</script>
