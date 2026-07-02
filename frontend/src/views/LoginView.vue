<template>
  <main class="section">
    <div class="section-inner" style="max-width: 460px">
      <NCard title="登录 TPMS-FORGE" :bordered="false">
        <NForm label-placement="top" @submit.prevent="submit">
          <NFormItem label="用户名">
            <NInput v-model:value="username" placeholder="researcher" />
          </NFormItem>
          <NFormItem label="密码">
            <NInput v-model:value="password" type="password" placeholder="开发期可输入任意密码" />
          </NFormItem>
          <NFormItem label="角色">
            <NRadioGroup v-model:value="role">
              <NRadioButton v-for="option in roleOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </NRadioButton>
            </NRadioGroup>
          </NFormItem>
          <NAlert v-if="errorMessage" type="error" :title="errorMessage" style="margin-bottom: 16px" />
          <NButton type="primary" block attr-type="submit" :loading="auth.loading">进入工作台</NButton>
        </NForm>
      </NCard>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NAlert, NButton, NCard, NForm, NFormItem, NInput, NRadioButton, NRadioGroup } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore, type UserRole } from '@/stores/auth'
import { normalizeApiError } from '@/api/client'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('researcher')
const password = ref('')
const role = ref<UserRole>('user')
const errorMessage = ref('')
const roleOptions = [
  { label: '用户', value: 'user' },
  { label: '管理员', value: 'admin' },
]

async function submit() {
  errorMessage.value = ''

  try {
    await auth.login(username.value, password.value, role.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    router.push(redirect)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}
</script>
