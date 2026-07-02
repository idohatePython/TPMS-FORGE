import type { DashboardStats, ForgeTask, Project } from '@/types/domain'

export const dashboardStats: DashboardStats = {
  projects: 6,
  runningTasks: 2,
  completedTasks: 18,
  storageGb: 12.4,
}

export const projects: Project[] = [
  {
    id: 'p-1001',
    name: 'Gyroid 轻量化支架',
    owner: 'machuang',
    material: 'PLA',
    modelFile: 'bracket_raw.stl',
    updatedAt: '2026-07-03 10:35',
    status: 'running',
  },
  {
    id: 'p-1002',
    name: 'Schwarz-P 多孔夹具',
    owner: 'machuang',
    material: 'PETG',
    modelFile: 'fixture.obj',
    updatedAt: '2026-07-02 18:20',
    status: 'completed',
  },
  {
    id: 'p-1003',
    name: 'Diamond 热交换样件',
    owner: 'researcher',
    material: 'Resin',
    modelFile: 'heat_exchanger.stl',
    updatedAt: '2026-07-01 14:08',
    status: 'queued',
  },
]

export const tasks: ForgeTask[] = [
  {
    id: 'mg-2048',
    projectId: 'p-1001',
    name: 'Gyroid 边界填充生成',
    type: 'model-generation',
    status: 'running',
    progress: 64,
    updatedAt: '2026-07-03 10:41',
  },
  {
    id: 'sg-1024',
    projectId: 'p-1002',
    name: '0.2mm 层高 G-code',
    type: 'slicing-gcode',
    status: 'completed',
    progress: 100,
    updatedAt: '2026-07-02 19:04',
  },
  {
    id: 'mg-2049',
    projectId: 'p-1003',
    name: 'Diamond 单元阵列预览',
    type: 'model-generation',
    status: 'queued',
    progress: 0,
    updatedAt: '2026-07-01 14:12',
  },
]

export function findProject(id: string) {
  return projects.find((project) => project.id === id) ?? projects[0]
}

export function findTask(id: string) {
  return tasks.find((task) => task.id === id) ?? tasks[0]
}
