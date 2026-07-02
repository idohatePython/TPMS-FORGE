import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

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
  const token = ref(user.value ? 'mock-token' : '')

  const isAuthenticated = computed(() => Boolean(user.value && token.value))
  const role = computed<UserRole>(() => user.value?.role ?? 'user')

  function login(username: string, selectedRole: UserRole = 'user') {
    const nextUser: AuthUser = {
      id: selectedRole === 'admin' ? 'admin-001' : 'user-001',
      username: username.trim() || (selectedRole === 'admin' ? 'admin' : 'researcher'),
      role: selectedRole,
    }

    user.value = nextUser
    token.value = 'mock-token'
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextUser))
  }

  function logout() {
    user.value = null
    token.value = ''
    localStorage.removeItem(STORAGE_KEY)
  }

  return {
    user,
    token,
    role,
    isAuthenticated,
    login,
    logout,
  }
})
