<template>
  <main>
    <section class="hero">
      <div class="hero-glow hero-glow-one" />
      <div class="hero-glow hero-glow-two" />
      <div class="hero-inner">
        <div class="hero-copy">
          <p class="hero-kicker">TPMS STRUCTURE TOOLCHAIN</p>
          <h1>从几何，<br>到可打印路径。</h1>
          <p class="hero-lead">
            生成可控的 TPMS 结构，完成模型切片，并在浏览器中检查每一层真实打印路径。
          </p>
          <div class="hero-actions">
            <NButton type="primary" size="large" color="#115e67" @click="router.push('/login')">
              进入工作台
            </NButton>
            <NButton secondary size="large" @click="router.push('/demo')">查看基础 Demo</NButton>
          </div>
          <div class="hero-capabilities">
            <span>STL / OBJ</span>
            <i />
            <span>TPMS</span>
            <i />
            <span>OrcaSlicer</span>
            <i />
            <span>G-code</span>
          </div>
        </div>
      </div>
    </section>

    <section class="section home-workflow">
      <div class="section-inner">
        <div class="home-section-heading">
          <p class="eyebrow">ONE CONNECTED WORKFLOW</p>
          <h2>一条完整、可追踪的制造流程。</h2>
          <p>每一步都保留参数、任务状态和输出文件，让结构设计能够被检查、复现和继续加工。</p>
        </div>

        <div class="workflow-grid">
          <article>
            <span>01</span>
            <h3>定义结构</h3>
            <p>上传模型，设置晶胞、数量、壁厚与边界模式，生成真实 TPMS 网格。</p>
          </article>
          <article>
            <span>02</span>
            <h3>完成切片</h3>
            <p>选择 OrcaSlicer 配置，将耗时计算交给后台任务，保留完整参数记录。</p>
          </article>
          <article>
            <span>03</span>
            <h3>检查路径</h3>
            <p>逐层、逐行查看 G-code 路径，定位打印类型、空驶和潜在问题。</p>
          </article>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { NButton } from 'naive-ui'
import { useRouter } from 'vue-router'

const router = useRouter()
</script>
