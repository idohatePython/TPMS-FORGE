<template>
  <NLayout has-sider class="workspace-layout">
    <NLayoutSider v-model:collapsed="collapsed" class="workspace-sider" bordered collapse-mode="width" :collapsed-width="72" :width="248" show-trigger>
      <div class="sider-brand">
        <span class="brand-mark">TF</span>
        <div v-if="!collapsed">
          <strong>TPMS-FORGE</strong>
          <small>{{ auth.user?.username ?? 'researcher' }}</small>
        </div>
      </div>
      <NMenu :options="menuOptions" :value="activeKey" @update:value="handleMenuSelect" />
    </NLayoutSider>

    <NLayout class="workspace-main">
      <NLayoutHeader class="workspace-header" bordered>
        <div>
          <p class="eyebrow">WORKSPACE</p>
          <h1>{{ route.meta.title ?? 'TPMS-FORGE' }}</h1>
        </div>
        <NSpace align="center">
          <NTag :type="auth.role === 'admin' ? 'warning' : 'info'" round>
            {{ auth.role === 'admin' ? 'Admin' : 'User' }}
          </NTag>
          <NButton secondary @click="logout">退出</NButton>
        </NSpace>
      </NLayoutHeader>
      <NLayoutContent class="workspace-content">
        <RouterView />
      </NLayoutContent>
    </NLayout>
  </NLayout>
</template>

<script setup lang="ts">
import type { MenuOption } from 'naive-ui'
import { NButton, NLayout, NLayoutContent, NLayoutHeader, NLayoutSider, NMenu, NSpace, NTag } from 'naive-ui'
import { computed, h, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)
const rememberedProjectId = ref(localStorage.getItem('tpms-forge-active-project'))
const routeProjectId = computed(() => typeof route.params.id === 'string' ? route.params.id : null)
const projectId = computed(() => routeProjectId.value ?? rememberedProjectId.value)

watch(routeProjectId, (value) => {
  if (!value) return
  rememberedProjectId.value = value
  localStorage.setItem('tpms-forge-active-project', value)
}, { immediate: true })

function projectToolLabel(label: string) {
  if (projectId.value) {
    return () => h(RouterLink, { to: projectToolPath(label) }, { default: () => label })
  }
  return () => h('span', { title: '请先在项目管理中选择一个项目' }, label)
}

function projectToolPath(label: string) {
  const suffix: Record<string, string> = {
    '模型导入': 'upload',
    '切片与 G-code': 'slicing',
  }
  return `/projects/${projectId.value}/${suffix[label]}`
}

const menuOptions = computed<MenuOption[]>(() => {
  const base: MenuOption[] = [
    { label: () => h(RouterLink, { to: '/dashboard' }, { default: () => '工作台' }), key: 'dashboard' },
    { label: () => h(RouterLink, { to: '/projects' }, { default: () => '项目管理' }), key: 'projects' },
  ]

  base.push(
    {
      label: projectToolLabel('模型导入'),
      key: 'upload',
      disabled: !projectId.value,
    },
    {
      label: projectToolLabel('切片与 G-code'),
      key: 'slicing',
      disabled: !projectId.value,
    },
  )

  if (auth.role === 'admin') {
    base.push({
      label: '管理员',
      key: 'admin-group',
      children: [
        { label: () => h(RouterLink, { to: '/admin' }, { default: () => '系统概览' }), key: 'admin' },
        { label: () => h(RouterLink, { to: '/admin/users' }, { default: () => '用户管理' }), key: 'admin-users' },
        { label: () => h(RouterLink, { to: '/admin/tasks' }, { default: () => '任务审计' }), key: 'admin-tasks' },
      ],
    })
  }

  return base
})

const activeKey = computed(() => {
  const name = String(route.name ?? '')

  if (name.includes('upload')) return 'upload'
  if (name.includes('files')) return 'files'
  if (name.includes('slicing')) return 'slicing'
  if (name.includes('admin-users')) return 'admin-users'
  if (name.includes('admin-tasks')) return 'admin-tasks'
  if (name.includes('admin')) return 'admin'
  if (name.includes('project')) return 'projects'
  return name || 'dashboard'
})

function handleMenuSelect() {
  return
}

function logout() {
  auth.logout()
  router.push('/')
}
</script>
