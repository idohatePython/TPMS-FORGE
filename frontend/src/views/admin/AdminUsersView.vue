<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">ADMIN USERS</p>
        <h1>用户管理</h1>
        <p>后续由管理员创建账号、分配角色并停用异常用户。</p>
      </div>
      <NButton type="primary">创建用户</NButton>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <NCard :bordered="false">
      <NDataTable :columns="columns" :data="users" :loading="loading" :pagination="false" />
    </NCard>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NAlert, NButton, NCard, NDataTable, NTag } from 'naive-ui'
import { h, onMounted, ref } from 'vue'

import { normalizeApiError } from '@/api/client'
import { listAdminUsersApi, type AdminUser } from '@/api/workspace'

const users = ref<AdminUser[]>([])
const loading = ref(false)
const errorMessage = ref('')

const columns: DataTableColumns<AdminUser> = [
  { title: '用户名', key: 'username' },
  { title: '角色', key: 'role' },
  { title: '状态', key: 'status', render: (row) => h(NTag, { type: 'success' }, { default: () => row.status }) },
  { title: '最近活跃', key: 'lastActive' },
]

async function loadUsers() {
  loading.value = true
  errorMessage.value = ''

  try {
    users.value = await listAdminUsersApi()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

onMounted(loadUsers)
</script>
