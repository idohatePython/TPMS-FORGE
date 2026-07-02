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
}

export interface DashboardStats {
  projects: number
  runningTasks: number
  completedTasks: number
  storageGb: number
}
