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
import { getProjectApi, uploadProjectFileApi } from '@/api/workspace'
import type { Project } from '@/types/domain'

const route = useRoute()
const project = ref<Project | null>(null)
const errorMessage = ref('')
const successMessage = ref('')

async function loadProject() {
  errorMessage.value = ''

  try {
    project.value = await getProjectApi(String(route.params.id))
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

    const uploadedFile = await uploadProjectFileApi(String(route.params.id), rawFile)
    successMessage.value = `${uploadedFile.filename} 已被后端接收`
    options.onFinish()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    options.onError()
  }
}

onMounted(loadProject)
watch(() => route.params.id, loadProject)
</script>
