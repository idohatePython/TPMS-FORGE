export type TaskStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface Project {
  id: string
  name: string
  owner: string
  material: string
  modelFile: string
  updatedAt: string
  status: TaskStatus
}

export interface ForgeTask {
  id: string
  projectId: string
  name: string
  type: 'model-generation' | 'slicing-gcode'
  status: TaskStatus
  progress: number
  updatedAt: string
  stage: string | null
  errorMessage: string | null
  inputFilename: string | null
  intermediateFilename: string | null
  outputFilename: string | null
}

export interface DashboardStats {
  projects: number
  runningTasks: number
  completedTasks: number
  storageGb: number
}
