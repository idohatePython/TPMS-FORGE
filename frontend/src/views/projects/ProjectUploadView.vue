<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">UPLOAD</p>
        <h1>模型上传</h1>
        <p>V1.0 目标支持 STL/OBJ。当前页面先保留上传交互与文件校验提示位置。</p>
      </div>
    </div>

    <div class="grid-2">
      <NCard title="上传文件" :bordered="false">
        <NUpload directory-dnd :max="1" accept=".stl,.obj">
          <NUploadDragger>
            <div class="page">
              <NText strong>拖入 STL/OBJ 文件</NText>
              <NText depth="3">后续会上传到后端 StorageService 并绑定项目。</NText>
            </div>
          </NUploadDragger>
        </NUpload>
      </NCard>
      <NCard title="处理策略" :bordered="false">
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
import {
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NText,
  NUpload,
  NUploadDragger,
} from 'naive-ui'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { findProject } from '@/mocks/workspace'

const route = useRoute()
const project = computed(() => findProject(String(route.params.id)))
</script>
