import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { loginApi } from '@/api/auth'
import { clearAuthToken, loadAuthToken, saveAuthToken } from '@/api/client'

export type UserRole = 'user' | 'admin'

export interface AuthUser {
  id: string
  username: string
  role: UserRole
}

const STORAGE_KEY = 'tpms-forge-auth'

function loadSavedUser(): AuthUser | null {
  const raw = localStorage.getItem(STORAGE_KEY)

  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(loadSavedUser())
  const token = ref(loadAuthToken())
  const loading = ref(false)

  const isAuthenticated = computed(() => Boolean(user.value && token.value))
  const role = computed<UserRole>(() => user.value?.role ?? 'user')

  async function login(username: string, password: string, selectedRole: UserRole = 'user') {
    loading.value = true

    try {
      const response = await loginApi(
        username.trim() || (selectedRole === 'admin' ? 'admin' : 'researcher'),
        password,
        selectedRole,
      )

      user.value = response.user
      token.value = response.accessToken
      saveAuthToken(response.accessToken)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(response.user))
    } finally {
      loading.value = false
    }
  }

  function logout() {
    user.value = null
    token.value = ''
    clearAuthToken()
    localStorage.removeItem(STORAGE_KEY)
  }

  return {
    user,
    token,
    role,
    loading,
    isAuthenticated,
    login,
    logout,
  }
})
