<template>
  <NLayout class="public-layout">
    <NLayoutHeader class="public-header" bordered>
      <RouterLink class="brand" to="/">
        <span class="brand-mark">TF</span>
        <span>
          <strong>TPMS-FORGE</strong>
          <small>结构生成与打印路径规划平台</small>
        </span>
      </RouterLink>
      <nav class="public-nav">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/demo">Demo</RouterLink>
        <RouterLink to="/dev/health">健康检查</RouterLink>
        <NButton type="primary" secondary @click="router.push('/login')">登录</NButton>
      </nav>
    </NLayoutHeader>
    <NLayoutContent>
      <RouterView />
    </NLayoutContent>
  </NLayout>
</template>

<script setup lang="ts">
import { NButton, NLayout, NLayoutContent, NLayoutHeader } from 'naive-ui'
import { useRouter } from 'vue-router'

const router = useRouter()
</script>
