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

    <NCard :bordered="false">
      <NDataTable :columns="columns" :data="users" :pagination="false" />
    </NCard>
  </section>
</template>

<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'
import { NButton, NCard, NDataTable, NTag } from 'naive-ui'
import { h } from 'vue'

interface AdminUser {
  username: string
  role: string
  status: string
  lastActive: string
}

const users: AdminUser[] = [
  { username: 'machuang', role: 'admin', status: 'active', lastActive: '2026-07-03 10:48' },
  { username: 'researcher', role: 'user', status: 'active', lastActive: '2026-07-02 21:18' },
]

const columns: DataTableColumns<AdminUser> = [
  { title: '用户名', key: 'username' },
  { title: '角色', key: 'role' },
  { title: '状态', key: 'status', render: (row) => h(NTag, { type: 'success' }, { default: () => row.status }) },
  { title: '最近活跃', key: 'lastActive' },
]
</script>
