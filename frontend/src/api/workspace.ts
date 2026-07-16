import { apiClient } from '@/api/client'
import type { DashboardStats, ForgeTask, Project } from '@/types/domain'

interface ProjectResponse {
  id: string
  name: string
  owner: string
  material: string
  model_file: string
  updated_at: string
  status: Project['status']
}

interface TaskResponse {
  id: string
  project_id: string
  name: string
  type: ForgeTask['type']
  status: ForgeTask['status']
  progress: number
  updated_at: string
}

interface DashboardStatsResponse {
  projects: number
  running_tasks: number
  completed_tasks: number
  storage_gb: number
}

interface FileUploadResponse {
  project_id: string
  filename: string
  content_type: string | null
  size_bytes: number
  status: 'accepted'
  file_url: string
}

interface SlicingRunResponse {
  task: TaskResponse
  gcode_filename: string
  gcode_url: string
}

interface AdminSummaryResponse {
  users: number
  projects: number
  tasks: number
}

interface AdminUserResponse {
  username: string
  role: string
  status: string
  last_active: string
}

export interface AdminSummary {
  users: number
  projects: number
  tasks: number
}

export interface AdminUser {
  username: string
  role: string
  status: string
  lastActive: string
}

export interface UploadedFile {
  projectId: string
  filename: string
  contentType: string | null
  sizeBytes: number
  status: 'accepted'
  fileUrl: string
}

export interface SlicingRun {
  task: ForgeTask
  gcodeFilename: string
  gcodeUrl: string
}

function mapProject(project: ProjectResponse): Project {
  return {
    id: project.id,
    name: project.name,
    owner: project.owner,
    material: project.material,
    modelFile: project.model_file,
    updatedAt: project.updated_at,
    status: project.status,
  }
}

function mapTask(task: TaskResponse): ForgeTask {
  return {
    id: task.id,
    projectId: task.project_id,
    name: task.name,
    type: task.type,
    status: task.status,
    progress: task.progress,
    updatedAt: task.updated_at,
  }
}

function mapDashboardStats(stats: DashboardStatsResponse): DashboardStats {
  return {
    projects: stats.projects,
    runningTasks: stats.running_tasks,
    completedTasks: stats.completed_tasks,
    storageGb: stats.storage_gb,
  }
}

function mapUploadedFile(file: FileUploadResponse): UploadedFile {
  return {
    projectId: file.project_id,
    filename: file.filename,
    contentType: file.content_type,
    sizeBytes: file.size_bytes,
    status: file.status,
    fileUrl: file.file_url,
  }
}

export async function getDashboardStatsApi() {
  const response = await apiClient.get<DashboardStatsResponse>('/dashboard/stats')
  return mapDashboardStats(response.data)
}

export async function listProjectsApi() {
  const response = await apiClient.get<ProjectResponse[]>('/projects')
  return response.data.map(mapProject)
}

export async function getProjectApi(projectId: string) {
  const response = await apiClient.get<ProjectResponse>(`/projects/${projectId}`)
  return mapProject(response.data)
}

export async function listProjectTasksApi(projectId: string) {
  const response = await apiClient.get<TaskResponse[]>(`/projects/${projectId}/tasks`)
  return response.data.map(mapTask)
}

export async function getModelTaskApi(taskId: string) {
  const response = await apiClient.get<TaskResponse>(`/model-tasks/${taskId}`)
  return mapTask(response.data)
}

export async function getSlicingTaskApi(taskId: string) {
  const response = await apiClient.get<TaskResponse>(`/slicing-tasks/${taskId}`)
  return mapTask(response.data)
}

export async function uploadProjectFileApi(projectId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<FileUploadResponse>(`/projects/${projectId}/files`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

  return mapUploadedFile(response.data)
}

export async function getLatestProjectFileApi(projectId: string) {
  const response = await apiClient.get<FileUploadResponse>(`/projects/${projectId}/files/latest`)
  return mapUploadedFile(response.data)
}

export async function listProjectFilesApi(projectId: string) {
  const response = await apiClient.get<FileUploadResponse[]>(`/projects/${projectId}/files`)
  return response.data.map(mapUploadedFile)
}

export async function listProjectGcodeFilesApi(projectId: string) {
  const response = await apiClient.get<FileUploadResponse[]>(`/projects/${projectId}/files/gcodes`)
  return response.data.map(mapUploadedFile)
}

export async function deleteProjectFileApi(projectId: string, filename: string) {
  await apiClient.delete(`/projects/${projectId}/files/${encodeURIComponent(filename)}`)
}

export async function deleteProjectGcodeFileApi(projectId: string, filename: string) {
  await apiClient.delete(`/projects/${projectId}/files/gcodes/${encodeURIComponent(filename)}`)
}

export async function createSlicingTaskApi(
  projectId: string,
  params: {
    inputFilename?: string
    layerHeight: number
    lineWidth: number
    printSpeed: number
    travelSpeed: number
    wallLoops: number
    topShellLayers: number
    bottomShellLayers: number
    sparseInfillDensity: number
    sparseInfillPattern: string
    enableSupport: boolean
    supportType: string
    brimWidth: number
    nozzleTemperature: number
    bedTemperature: number
    filamentType: string
  },
): Promise<SlicingRun> {
  const response = await apiClient.post<SlicingRunResponse>(`/projects/${projectId}/slicing-tasks`, {
    input_filename: params.inputFilename,
    layer_height: params.layerHeight,
    line_width: params.lineWidth,
    print_speed: params.printSpeed,
    travel_speed: params.travelSpeed,
    wall_loops: params.wallLoops,
    top_shell_layers: params.topShellLayers,
    bottom_shell_layers: params.bottomShellLayers,
    sparse_infill_density: params.sparseInfillDensity,
    sparse_infill_pattern: params.sparseInfillPattern,
    enable_support: params.enableSupport,
    support_type: params.supportType,
    brim_width: params.brimWidth,
    nozzle_temperature: params.nozzleTemperature,
    bed_temperature: params.bedTemperature,
    filament_type: params.filamentType,
  })

  return {
    task: mapTask(response.data.task),
    gcodeFilename: response.data.gcode_filename,
    gcodeUrl: response.data.gcode_url,
  }
}

export async function getAdminSummaryApi(): Promise<AdminSummary> {
  const response = await apiClient.get<AdminSummaryResponse>('/admin/summary')
  return response.data
}

export async function listAdminTasksApi() {
  const response = await apiClient.get<TaskResponse[]>('/admin/tasks')
  return response.data.map(mapTask)
}

export async function listAdminUsersApi() {
  const response = await apiClient.get<AdminUserResponse[]>('/admin/users')
  return response.data.map((user) => ({
    username: user.username,
    role: user.role,
    status: user.status,
    lastActive: user.last_active,
  }))
}
