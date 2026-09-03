import { apiClient } from '@/api/client'

export type DemoTpmsType = 'gyroid' | 'schwarz_p' | 'diamond' | 'iwp' | 'neovius' | 'lidinoid'
export type DemoQuality = 'fast' | 'standard'

export interface DemoTpmsRequest {
  tpmsType: DemoTpmsType
  cellSize: number
  cellCount: number
  wallThicknessMm: number
  quality: DemoQuality
  gradientAxis: 'x' | 'y' | 'z'
  gradientStartOffset: number
  gradientEndOffset: number
}

export interface DemoTpmsMesh {
  data: ArrayBuffer
  vertexCount: number
  triangleCount: number
  durationMs: number
}

export async function generateDemoTpmsApi(
  payload: DemoTpmsRequest,
): Promise<DemoTpmsMesh> {
  const response = await apiClient.post<ArrayBuffer>(
    '/demo/tpms',
    {
      tpms_type: payload.tpmsType,
      cell_size: payload.cellSize,
      cell_count: payload.cellCount,
      wall_thickness_mm: payload.wallThicknessMm,
      quality: payload.quality,
      gradient_axis: payload.gradientAxis,
      gradient_start_offset: payload.gradientStartOffset,
      gradient_end_offset: payload.gradientEndOffset,
    },
    {
      responseType: 'arraybuffer',
      timeout: 60000,
    },
  )

  return {
    data: response.data,
    vertexCount: Number(response.headers['x-tpms-vertices'] ?? 0),
    triangleCount: Number(response.headers['x-tpms-triangles'] ?? 0),
    durationMs: Number(response.headers['x-tpms-duration-ms'] ?? 0),
  }
}
