import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  timeout: 10000,
})

export interface ApiError {
  status?: number
  message: string
  code?: string
}

export function normalizeApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const data = error.response?.data as { detail?: string; message?: string; code?: string } | undefined

    return {
      status,
      message: data?.detail ?? data?.message ?? error.message ?? '请求失败',
      code: data?.code,
    }
  }

  if (error instanceof Error) {
    return { message: error.message }
  }

  return { message: '未知错误' }
}
