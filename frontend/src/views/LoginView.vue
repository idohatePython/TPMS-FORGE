<template>
  <main class="section">
    <div class="section-inner" style="max-width: 460px">
      <NCard title="登录 TPMS-FORGE" :bordered="false">
        <NForm label-placement="top" @submit.prevent="submit">
          <NFormItem label="用户名">
            <NInput v-model:value="username" placeholder="researcher" />
          </NFormItem>
          <NFormItem label="密码">
            <NInput v-model:value="password" type="password" placeholder="当前为前端占位登录" />
          </NFormItem>
          <NFormItem label="角色">
            <NRadioGroup v-model:value="role">
              <NRadioButton v-for="option in roleOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </NRadioButton>
            </NRadioGroup>
          </NFormItem>
          <NButton type="primary" block attr-type="submit">进入工作台</NButton>
        </NForm>
      </NCard>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NCard, NForm, NFormItem, NInput, NRadioButton, NRadioGroup } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore, type UserRole } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('researcher')
const password = ref('')
const role = ref<UserRole>('user')
const roleOptions = [
  { label: '用户', value: 'user' },
  { label: '管理员', value: 'admin' },
]

function submit() {
  auth.login(username.value, role.value)
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
  router.push(redirect)
}
</script>
