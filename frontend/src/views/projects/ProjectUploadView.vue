<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">UPLOAD</p>
        <h1>模型上传</h1>
        <p>V1.0 目标支持 STL/OBJ。当前页面先保留上传交互与文件校验提示位置。</p>
      </div>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />
    <NAlert v-if="successMessage" type="success" :title="successMessage" />

    <div class="grid-2">
      <NCard title="上传文件" :bordered="false">
        <NUpload
          directory-dnd
          :max="1"
          accept=".stl,.obj"
          :custom-request="uploadFile"
        >
          <NUploadDragger>
            <div class="page">
              <NText strong>拖入 STL/OBJ 文件</NText>
              <NText depth="3">后续会上传到后端 StorageService 并绑定项目。</NText>
            </div>
          </NUploadDragger>
        </NUpload>
      </NCard>
      <NCard v-if="project" title="处理策略" :bordered="false">
        <NDescriptions :column="1" label-placement="left">
          <NDescriptionsItem label="项目">{{ project.name }}</NDescriptionsItem>
          <NDescriptionsItem label="允许格式">STL / OBJ</NDescriptionsItem>
          <NDescriptionsItem label="存储">本地文件系统抽象层</NDescriptionsItem>
        </NDescriptions>
      </NCard>
    </div>

    <NCard title="模型预览" :bordered="false">
      <ModelPreview
        :source-url="uploadedFile ? absoluteFileUrl(uploadedFile.fileUrl) : undefined"
        :filename="uploadedFile?.filename"
      />
    </NCard>
  </section>
</template>

<script setup lang="ts">
import type { UploadCustomRequestOptions } from 'naive-ui'
import {
  NAlert,
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NText,
  NUpload,
  NUploadDragger,
} from 'naive-ui'
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import ModelPreview from '@/components/ModelPreview.vue'
import { getLatestProjectFileApi, getProjectApi, uploadProjectFileApi, type UploadedFile } from '@/api/workspace'
import type { Project } from '@/types/domain'

const route = useRoute()
const project = ref<Project | null>(null)
const uploadedFile = ref<UploadedFile | null>(null)
const errorMessage = ref('')
const successMessage = ref('')

function absoluteFileUrl(fileUrl: string) {
  return `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}${fileUrl.replace('/api/v1', '')}`
}

async function loadProject() {
  errorMessage.value = ''

  try {
    const projectId = String(route.params.id)
    project.value = await getProjectApi(projectId)
    try {
      uploadedFile.value = await getLatestProjectFileApi(projectId)
    } catch {
      uploadedFile.value = null
    }
  } catch (error) {
    project.value = null
    errorMessage.value = normalizeApiError(error).message
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
    successMessage.value = `${uploadedFile.value.filename} 已被后端接收`
    options.onFinish()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    options.onError()
  }
}

onMounted(loadProject)
watch(() => route.params.id, loadProject)
</script>
