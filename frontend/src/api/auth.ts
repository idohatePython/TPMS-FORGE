import { apiClient } from '@/api/client'
import type { AuthUser } from '@/stores/auth'

interface LoginResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export async function loginApi(identifier: string, password: string) {
  const response = await apiClient.post<LoginResponse>('/auth/login', {
    identifier,
    password,
  })

  return {
    accessToken: response.data.access_token,
    tokenType: response.data.token_type,
    user: response.data.user,
  }
}

export async function getCurrentUserApi() {
  const response = await apiClient.get<AuthUser>('/auth/me')
  return response.data
}