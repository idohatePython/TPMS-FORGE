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
  stage?: string | null
  error_message?: string | null
  input_filename?: string | null
  intermediate_filename?: string | null
  output_filename?: string | null
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
  file_kind: 'uploaded_model' | 'generated_model' | 'gcode'
  source_task_id: string | null
  created_at: string
  temporary: boolean
  expires_at: string | null
}

interface SlicingRunResponse {
  task: TaskResponse
  gcode_filename: string
  gcode_url: string
  intermediate_model_filename: string | null
  intermediate_model_url: string | null
}

interface SlicerStatusResponse {
  engine: string
  available: boolean
  executable: string | null
  message: string
}

interface ModelGenerationRunResponse {
  task: TaskResponse
  model_filename: string
  model_url: string
  vertices: number
  triangles: number
  volume_mm3: number
  surface_area_mm2: number
  relative_density: number
  effective_level_set_offset: number
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
  fileKind: 'uploaded_model' | 'generated_model' | 'gcode'
  sourceTaskId: string | null
  createdAt: string
  temporary: boolean
  expiresAt: string | null
}

export interface SlicingRun {
  task: ForgeTask
  gcodeFilename: string
  gcodeUrl: string
  intermediateModelFilename: string | null
  intermediateModelUrl: string | null
}

export interface SlicerStatus {
  engine: string
  available: boolean
  executable: string | null
  message: string
}

export interface ModelGenerationRun {
  task: ForgeTask
  modelFilename: string
  modelUrl: string
  vertices: number
  triangles: number
  volumeMm3: number
  surfaceAreaMm2: number
  relativeDensity: number
  effectiveLevelSetOffset: number
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
    stage: task.stage ?? null,
    errorMessage: task.error_message ?? null,
    inputFilename: task.input_filename ?? null,
    intermediateFilename: task.intermediate_filename ?? null,
    outputFilename: task.output_filename ?? null,
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
    fileKind: file.file_kind,
    sourceTaskId: file.source_task_id,
    createdAt: file.created_at,
    temporary: file.temporary,
    expiresAt: file.expires_at,
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

export async function createProjectApi(name: string, material: string) {
  const response = await apiClient.post<ProjectResponse>('/projects', { name, material })
  return mapProject(response.data)
}

export async function getProjectApi(projectId: string) {
  const response = await apiClient.get<ProjectResponse>(`/projects/${projectId}`)
  return mapProject(response.data)
}

export async function updateProjectNameApi(projectId: string, name: string) {
  const response = await apiClient.patch<ProjectResponse>(`/projects/${projectId}`, { name })
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

export async function getSlicerStatusApi(): Promise<SlicerStatus> {
  const response = await apiClient.get<SlicerStatusResponse>('/slicing-tasks/engine/status')
  return {
    engine: response.data.engine,
    available: response.data.available,
    executable: response.data.executable,
    message: response.data.message,
  }
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

export async function selectLatestProjectFileApi(projectId: string, filename: string) {
  const response = await apiClient.post<FileUploadResponse>(`/projects/${projectId}/files/latest`, {
    filename,
  })
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

export async function createModelTaskApi(
  projectId: string,
  params: {
    generationDomain: 'block' | 'boundary'
    boundaryMode: 'auto' | 'closed' | 'footprint'
    tpmsType: 'gyroid' | 'schwarz_p' | 'diamond' | 'iwp' | 'neovius' | 'lidinoid'
    structureType: 'sheet' | 'rod_negative' | 'rod_positive'
    cellSize: number
    cellSizeX: number
    cellSizeY: number
    cellSizeZ: number
    cellCountX: number
    cellCountY: number
    cellCountZ: number
    wallThicknessMm: number
    levelSetOffset: number
    phaseShiftX: number
    phaseShiftY: number
    phaseShiftZ: number
    gradientAxis: 'none' | 'x' | 'y' | 'z'
    gradientStrength: number
    densityGradientMode: 'none' | 'linear'
    densityGradientAxis: 'x' | 'y' | 'z' | 'radial'
    densityGradientStartOffset: number
    densityGradientEndOffset: number
    densityGradientCurve: 'linear' | 'smooth' | 'ease_in' | 'ease_out'
    thicknessGradientMode: 'none' | 'linear'
    thicknessGradientAxis: 'x' | 'y' | 'z' | 'radial'
    thicknessGradientStartMm: number
    thicknessGradientEndMm: number
    thicknessGradientCurve: 'linear' | 'smooth' | 'ease_in' | 'ease_out'
    densityMode: 'manual' | 'target'
    targetRelativeDensity: number
    gyroidTermWeight: number
    schwarzCrossWeight: number
    diamondNodalWeight: number
    iwpSecondHarmonicWeight: number
    neoviusProductWeight: number
    lidinoidHarmonicWeight: number
    lidinoidBias: number
    invertField: boolean
    quality: 'fast' | 'standard' | 'high'
  },
): Promise<ModelGenerationRun> {
  const response = await apiClient.post<ModelGenerationRunResponse>(
    `/projects/${projectId}/model-tasks`,
    {
      generation_domain: params.generationDomain,
      boundary_mode: params.boundaryMode,
      tpms_type: params.tpmsType,
      structure_type: params.structureType,
      cell_size: params.cellSize,
      cell_size_x: params.cellSizeX,
      cell_size_y: params.cellSizeY,
      cell_size_z: params.cellSizeZ,
      cell_count_x: params.cellCountX,
      cell_count_y: params.cellCountY,
      cell_count_z: params.cellCountZ,
      wall_thickness_mm: params.wallThicknessMm,
      level_set_offset: params.levelSetOffset,
      phase_shift_x: params.phaseShiftX,
      phase_shift_y: params.phaseShiftY,
      phase_shift_z: params.phaseShiftZ,
      gradient_axis: params.gradientAxis,
      gradient_strength: params.gradientStrength,
      density_gradient_mode: params.densityGradientMode,
      density_gradient_axis: params.densityGradientAxis,
      density_gradient_start_offset: params.densityGradientStartOffset,
      density_gradient_end_offset: params.densityGradientEndOffset,
      density_gradient_curve: params.densityGradientCurve,
      thickness_gradient_mode: params.thicknessGradientMode,
      thickness_gradient_axis: params.thicknessGradientAxis,
      thickness_gradient_start_mm: params.thicknessGradientStartMm,
      thickness_gradient_end_mm: params.thicknessGradientEndMm,
      thickness_gradient_curve: params.thicknessGradientCurve,
      density_mode: params.densityMode,
      target_relative_density: params.targetRelativeDensity,
      gyroid_term_weight: params.gyroidTermWeight,
      schwarz_cross_weight: params.schwarzCrossWeight,
      diamond_nodal_weight: params.diamondNodalWeight,
      iwp_second_harmonic_weight: params.iwpSecondHarmonicWeight,
      neovius_product_weight: params.neoviusProductWeight,
      lidinoid_harmonic_weight: params.lidinoidHarmonicWeight,
      lidinoid_bias: params.lidinoidBias,
      invert_field: params.invertField,
      quality: params.quality,
    },
    { timeout: 300_000 },
  )

  return {
    task: mapTask(response.data.task),
    modelFilename: response.data.model_filename,
    modelUrl: response.data.model_url,
    vertices: response.data.vertices,
    triangles: response.data.triangles,
    volumeMm3: response.data.volume_mm3,
    surfaceAreaMm2: response.data.surface_area_mm2,
    relativeDensity: response.data.relative_density,
    effectiveLevelSetOffset: response.data.effective_level_set_offset,
  }
}

export async function createSlicingTaskApi(
  projectId: string,
  params: {
    inputFilename?: string
    slicingEngine: 'orca' | 'vsp'
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
    infillMode: 'standard' | 'tpms'
    tpmsType: 'gyroid' | 'schwarz_p' | 'diamond' | 'iwp' | 'neovius' | 'lidinoid'
    tpmsStructureType: 'sheet' | 'rod_negative' | 'rod_positive'
    tpmsCellSize: number
    tpmsWallThickness: number
    tpmsLevelSetOffset: number
    tpmsGradientTarget: 'density' | 'thickness'
    tpmsGradientAxis: 'x' | 'y' | 'z' | 'radial'
    tpmsGradientStart: number
    tpmsGradientEnd: number
    tpmsGradientCurve: 'linear' | 'smooth' | 'ease_in' | 'ease_out'
    tpmsPhaseX: number
    tpmsPhaseY: number
    tpmsPhaseZ: number
    tpmsInvertField: boolean
    tpmsQuality: 'fast' | 'standard' | 'high'
  },
): Promise<SlicingRun> {
  const response = await apiClient.post<SlicingRunResponse>(
    `/projects/${projectId}/slicing-tasks`,
    {
      input_filename: params.inputFilename,
      slicing_engine: params.slicingEngine,
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
      infill_mode: params.infillMode,
      tpms_type: params.tpmsType,
      tpms_structure_type: params.tpmsStructureType,
      tpms_cell_size: params.tpmsCellSize,
      tpms_wall_thickness_mm: params.tpmsWallThickness,
      tpms_level_set_offset: params.tpmsLevelSetOffset,
      tpms_gradient_target: params.tpmsGradientTarget,
      tpms_gradient_axis: params.tpmsGradientAxis,
      tpms_gradient_start: params.tpmsGradientStart,
      tpms_gradient_end: params.tpmsGradientEnd,
      tpms_gradient_curve: params.tpmsGradientCurve,
      tpms_phase_x: params.tpmsPhaseX,
      tpms_phase_y: params.tpmsPhaseY,
      tpms_phase_z: params.tpmsPhaseZ,
      tpms_invert_field: params.tpmsInvertField,
      tpms_quality: params.tpmsQuality,
    },
    { timeout: 300_000 },
  )

  return {
    task: mapTask(response.data.task),
    gcodeFilename: response.data.gcode_filename,
    gcodeUrl: response.data.gcode_url,
    intermediateModelFilename: response.data.intermediate_model_filename,
    intermediateModelUrl: response.data.intermediate_model_url,
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
