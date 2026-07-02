<template>
  <main>
    <section class="hero">
      <div class="hero-inner">
        <p class="eyebrow">TPMS STRUCTURE TOOLCHAIN</p>
        <h1>TPMS-FORGE</h1>
        <p>
          面向科研与工程验证的 TPMS 结构生成平台，从 STL/OBJ 模型、TPMS 填充、切片路径到
          Marlin G-code 输出，逐步跑通完整打印闭环。
        </p>
        <div class="hero-actions">
          <NButton type="primary" size="large" color="#f0a954" @click="router.push('/demo')">
            打开 Demo
          </NButton>
          <NButton ghost size="large" @click="router.push('/login')">进入工作台</NButton>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-inner page">
        <div class="page-heading">
          <div>
            <p class="eyebrow">V1.0 WORKFLOW</p>
            <h2>从模型到 G-code 的核心流程</h2>
          </div>
        </div>
        <div class="grid-3">
          <NCard title="模型上传" :bordered="false">
            支持 STL/OBJ 文件进入项目空间，后续由后端统一处理存储、鉴权与任务关联。
          </NCard>
          <NCard title="TPMS 生成" :bordered="false">
            以 Schwarz-P、Gyroid、Diamond 为首批结构，围绕参数面板与三维预览组织交互。
          </NCard>
          <NCard title="切片与下载" :bordered="false">
            切片任务生成路径与 Marlin G-code，完成后在项目内下载和追踪历史结果。
          </NCard>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { NButton, NCard } from 'naive-ui'
import { useRouter } from 'vue-router'

const router = useRouter()
</script>
