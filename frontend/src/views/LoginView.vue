<template>
  <main class="section login-page">
    <div class="section-inner login-container">
      <NCard :bordered="false" class="login-card">
        <div class="login-heading">
          <span class="brand-mark">TF</span>
          <div>
            <p class="eyebrow">TPMS-FORGE</p>
            <h1>登录工作台</h1>
            <p>使用用户名或邮箱登录，继续管理模型、TPMS 任务与切片结果。</p>
          </div>
        </div>

        <NForm label-placement="top" @submit.prevent="submit">
          <NFormItem
            label="用户名或邮箱"
            :validation-status="identifierError ? 'error' : undefined"
            :feedback="identifierError"
          >
            <NInput
              v-model:value="identifier"
              placeholder="请输入用户名或邮箱"
              autocomplete="username"
              clearable
              @update:value="identifierError = ''"
            />
          </NFormItem>

          <NFormItem
            label="密码"
            :validation-status="passwordError ? 'error' : undefined"
            :feedback="passwordError"
          >
            <NInput
              v-model:value="password"
              type="password"
              show-password-on="click"
              placeholder="请输入密码"
              autocomplete="current-password"
              @update:value="passwordError = ''"
            />
          </NFormItem>

          <NAlert
            v-if="errorMessage"
            type="error"
            :title="errorMessage"
            class="login-alert"
          />

          <NButton
            type="primary"
            block
            attr-type="submit"
            :loading="auth.loading"
            :disabled="auth.loading"
          >
            登录
          </NButton>
        </NForm>

        <div class="login-footer">
          <NButton text @click="router.push('/')">返回首页</NButton>
          <span>账号由管理员创建</span>
        </div>
      </NCard>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NForm,
  NFormItem,
  NInput,
} from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { normalizeApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const identifier = ref('')
const password = ref('')
const identifierError = ref('')
const passwordError = ref('')
const errorMessage = ref('')

function validateForm() {
  identifierError.value = ''
  passwordError.value = ''

  if (!identifier.value.trim()) {
    identifierError.value = '请输入用户名或邮箱'
  }

  if (!password.value) {
    passwordError.value = '请输入密码'
  }

  return !identifierError.value && !passwordError.value
}

async function submit() {
  errorMessage.value = ''

  if (!validateForm()) {
    return
  }

  try {
    await auth.login(identifier.value, password.value)

    const redirect =
      typeof route.query.redirect === 'string'
        ? route.query.redirect
        : '/dashboard'

    await router.push(redirect)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}
</script>
