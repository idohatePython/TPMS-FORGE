<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">SLICING</p>
        <h1>切片与 G-code</h1>
        <p>参考 Bambu Studio 的工作区布局，选择普通填充或 TPMS 梯度填充。</p>
      </div>
      <NSpace>
        <NButton :disabled="!gcodeUrl" @click="downloadGcode">下载 G-code</NButton>
        <NButton
          v-if="form.infillMode === 'tpms'"
          :disabled="selectedInputIsGenerated"
          :loading="generatingTpms"
          :title="selectedInputIsGenerated ? '当前已是 TPMS 生成模型，请直接开始切片或先选择原始模型' : undefined"
          @click="createTpmsModel"
        >
          {{ generatingTpms ? '正在生成 TPMS…' : selectedInputIsGenerated ? 'TPMS STL 已生成' : '生成 TPMS STL' }}
        </NButton>
        <NButton id="slicing-start-button" type="primary" :loading="slicing" @click="createSlicingTask">
          {{ form.infillMode === 'standard' ? '生成 G-code' : '开始切片' }}
        </NButton>
      </NSpace>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />
    <NAlert v-if="successMessage" type="success" :title="successMessage" />
    <NAlert
      v-if="slicerStatus"
      class="slicer-status-alert"
      :type="slicerStatus.available ? 'success' : 'warning'"
      :title="slicerStatus.available ? 'OrcaSlicer 已连接' : 'OrcaSlicer 未连接'"
    >
      {{ slicerStatus.available ? slicerStatus.executable : slicerStatus.message }}
    </NAlert>

    <nav class="slicer-stage-bar" aria-label="切片工作流">
      <button
        v-for="stage in workflowStages"
        :key="stage.index"
        type="button"
        class="slicer-stage"
        :class="{ active: currentStage === stage.index, complete: currentStage > stage.index }"
        :aria-current="currentStage === stage.index ? 'step' : undefined"
        @click="selectWorkflowStage(stage.index)"
      >
        <span class="slicer-stage-index">{{ currentStage > stage.index ? '✓' : stage.index }}</span>
        <span>
          <strong>{{ stage.label }}</strong>
          <small>{{ stage.description }}</small>
        </span>
      </button>
    </nav>

    <div class="slicer-workbench" :class="{ 'settings-collapsed': settingsCollapsed }">
      <NCard :bordered="false" class="slicer-viewport-card">
        <template #header>
          <NSpace justify="space-between" align="center">
            <div>
              <strong>{{ project?.name ?? route.params.id }}</strong>
              <small class="slicer-viewport-subtitle">固定工作视口 · 仅切换模型与路径数据</small>
            </div>
            <NSpace align="center">
              <NTag v-if="uploadedFile" round>{{ uploadedFile.filename }}</NTag>
              <NButton size="small" secondary @click="settingsCollapsed = !settingsCollapsed">
                {{ settingsCollapsed ? '展开参数' : '收起参数' }}
              </NButton>
            </NSpace>
          </NSpace>
        </template>
        <NTabs v-model:value="activePreview" type="line" animated>
          <NTabPane name="model" tab="模型">
            <div v-if="form.infillMode === 'standard'" class="slicer-model-preview-note">
              <NTag type="info" size="small">{{ form.sparseInfillPattern }} · {{ form.sparseInfillDensity }}%</NTag>
              <span>基于当前上传模型边界的三维晶格快速预览；生成 G-code 后可查看真实切片路径</span>
            </div>
            <ModelPreview
              :source-url="uploadedFile ? absoluteFileUrl(uploadedFile.fileUrl) : undefined"
              :filename="uploadedFile?.filename"
              :infill-pattern="form.infillMode === 'standard' ? form.sparseInfillPattern : undefined"
              :infill-density="form.infillMode === 'standard' ? form.sparseInfillDensity : undefined"
            />
          </NTabPane>
          <NTabPane name="toolpath" tab="切片路径">
            <GcodeLayerPreview :gcode-url="gcodeUrl || undefined" />
          </NTabPane>
        </NTabs>
      </NCard>

      <aside class="slicer-side-panel">
        <NCard title="填充方式" :bordered="false">
          <NRadioGroup v-model:value="form.infillMode" class="slicer-infill-mode">
            <NRadio value="standard" class="slicer-infill-option">
              <strong>普通填充</strong>
              <span>OrcaSlicer 内置填充，直接生成 G-code</span>
            </NRadio>
            <NRadio value="tpms" class="slicer-infill-option">
              <strong>TPMS 梯度填充</strong>
              <span>先在模型边界内生成 TPMS STL，再进行切片</span>
            </NRadio>
          </NRadioGroup>

          <NForm v-if="form.infillMode === 'standard'" label-placement="top" class="slicer-mode-parameters">
            <NAlert type="info" :bordered="false" class="slicing-engine-note">
              当前将把选中的原始 STL/OBJ 直接交给 OrcaSlicer，不生成 TPMS 中间模型。
            </NAlert>
            <NFormItem label="填充图案">
              <NSelect v-model:value="form.sparseInfillPattern" :options="infillOptions" />
            </NFormItem>
            <NFormItem label="填充密度">
              <NSlider v-model:value="form.sparseInfillDensity" :min="0" :max="100" />
              <span class="slicer-inline-value">{{ form.sparseInfillDensity }}%</span>
            </NFormItem>
            <div class="slicer-standard-actions">
              <NButton type="primary" block :loading="slicing" @click="createSlicingTask">生成 G-code</NButton>
            </div>
          </NForm>

          <NForm v-else label-placement="top" class="slicer-mode-parameters">
            <NAlert type="info" :bordered="false" class="slicing-engine-note">
              TPMS 类型就是本平台的核心填充形状；与普通 Gyroid/Grid 不同，它会先生成带梯度的 TPMS 结构，再交给切片器生成路径。
            </NAlert>
            <NAlert v-if="selectedInputIsGenerated" type="warning" class="slicing-engine-note">
              当前选择的是平台生成的 TPMS 模型，将直接切片。你仍可以修改下方参数；要生成新的结构，请在“切片模型”中选择原始模型后再点击“生成 TPMS STL”。若原始模型已自动清理，请先重新导入。
            </NAlert>
            <div class="slicing-form-grid">
              <NFormItem label="TPMS 类型">
                <NSelect v-model:value="form.tpmsType" :options="tpmsTypeOptions" />
              </NFormItem>
              <NFormItem label="结构模式">
                <NSelect v-model:value="form.tpmsStructureType" :options="tpmsStructureOptions" />
              </NFormItem>
            </div>
            <div class="slicing-form-grid">
              <NFormItem label="晶胞尺寸">
                <NInputNumber v-model:value="form.tpmsCellSize" :min="2" :max="30" :step="0.5">
                  <template #suffix>mm</template>
                </NInputNumber>
              </NFormItem>
              <NFormItem :label="form.tpmsStructureType === 'sheet' ? '壁厚' : '等值面偏移'">
                <NInputNumber
                  v-if="form.tpmsStructureType === 'sheet'"
                  v-model:value="form.tpmsWallThickness"
                  :min="0.2"
                  :max="6"
                  :step="0.1"
                />
                <NInputNumber v-else v-model:value="form.tpmsLevelSetOffset" :min="-1.5" :max="1.5" :step="0.05" />
              </NFormItem>
            </div>
            <div class="slicing-form-grid">
              <NFormItem label="梯度内容">
                <NSelect v-model:value="form.tpmsGradientTarget" :options="gradientTargetOptions" />
              </NFormItem>
              <NFormItem label="梯度方向">
                <NSelect v-model:value="form.tpmsGradientAxis" :options="gradientAxisOptions" />
              </NFormItem>
            </div>
            <div class="slicing-form-grid">
              <NFormItem label="起始值">
                <NInputNumber v-model:value="form.tpmsGradientStart" :min="gradientValueMin" :max="gradientValueMax" :step="0.1" />
              </NFormItem>
              <NFormItem label="结束值">
                <NInputNumber v-model:value="form.tpmsGradientEnd" :min="gradientValueMin" :max="gradientValueMax" :step="0.1" />
              </NFormItem>
            </div>
            <NFormItem label="变化曲线">
              <NSelect v-model:value="form.tpmsGradientCurve" :options="gradientCurveOptions" />
            </NFormItem>
            <NFormItem label="TPMS 网格质量">
              <NSelect v-model:value="form.tpmsQuality" :options="tpmsQualityOptions" />
            </NFormItem>
            <NCollapse>
              <NCollapseItem title="高级 TPMS 参数" name="advanced">
                <div class="slicing-form-grid">
                  <NFormItem label="X 相位">
                    <NInputNumber v-model:value="form.tpmsPhaseX" :min="-3.14" :max="3.14" :step="0.1" />
                  </NFormItem>
                  <NFormItem label="Y 相位">
                    <NInputNumber v-model:value="form.tpmsPhaseY" :min="-3.14" :max="3.14" :step="0.1" />
                  </NFormItem>
                </div>
                <NFormItem label="Z 相位">
                  <NInputNumber v-model:value="form.tpmsPhaseZ" :min="-3.14" :max="3.14" :step="0.1" />
                </NFormItem>
                <NFormItem label="反向结构">
                  <NSwitch v-model:value="form.tpmsInvertField" />
                </NFormItem>
              </NCollapseItem>
            </NCollapse>
            <div class="slicer-tpms-actions">
              <NButton
                secondary
                block
                :disabled="selectedInputIsGenerated || !selectedInputFilename"
                :loading="generatingTpms"
                @click="createTpmsModel"
              >
                {{ selectedInputIsGenerated ? 'TPMS STL 已生成' : generatingTpms ? '正在生成 TPMS…' : '生成 TPMS STL' }}
              </NButton>
              <NButton type="primary" block :loading="slicing" @click="createSlicingTask">开始切片</NButton>
            </div>
          </NForm>
        </NCard>

        <NCard title="材料与预设" :bordered="false">
          <NForm label-placement="top">
            <NFormItem label="切片方式">
              <NSelect v-model:value="form.slicingEngine" :options="slicingEngineOptions" />
            </NFormItem>
            <NAlert
              v-if="form.slicingEngine === 'vsp'"
              class="slicing-engine-note"
              type="warning"
              title="VSP 可变线宽路径仍处于实验阶段"
            >
              系统会逐层读取所选 STL/OBJ 的真实截面，再用 VSP 生成可变线宽中心路径。打印前请检查路径连续性与挤出宽度。
            </NAlert>
            <NFormItem label="切片模型">
              <NSelect v-model:value="selectedInputFilename" :options="savedFileOptions" />
            </NFormItem>
            <NFormItem label="Filament">
              <NSelect v-model:value="form.filamentType" :options="filamentOptions" />
            </NFormItem>
            <div class="slicing-form-grid">
              <NFormItem label="Nozzle Temp">
                <NInputNumber v-model:value="form.nozzleTemperature" :min="150" :max="320" />
              </NFormItem>
              <NFormItem label="Bed Temp">
                <NInputNumber v-model:value="form.bedTemperature" :min="0" :max="120" />
              </NFormItem>
            </div>
          </NForm>
        </NCard>

        <NCard title="质量与强度" :bordered="false">
          <NForm label-placement="top">
            <div class="slicing-form-grid">
              <NFormItem label="Layer Height">
                <NInputNumber v-model:value="form.layerHeight" :min="0.05" :max="0.6" :step="0.05" />
              </NFormItem>
              <NFormItem label="Line Width">
                <NInputNumber v-model:value="form.lineWidth" :min="0.2" :max="1.2" :step="0.05" />
              </NFormItem>
            </div>
            <div class="slicing-form-grid">
              <NFormItem label="Wall Loops">
                <NInputNumber v-model:value="form.wallLoops" :min="1" :max="8" />
              </NFormItem>
              <NFormItem label="Top / Bottom">
                <NSpace>
                  <NInputNumber v-model:value="form.topShellLayers" :min="0" :max="12" />
                  <NInputNumber v-model:value="form.bottomShellLayers" :min="0" :max="12" />
                </NSpace>
              </NFormItem>
            </div>
          </NForm>
        </NCard>

        <NCard title="速度与附着" :bordered="false">
          <NForm label-placement="top">
            <NFormItem label="Print Speed">
              <NSlider v-model:value="form.speed" :min="10" :max="120" />
            </NFormItem>
            <NFormItem label="Travel Speed">
              <NSlider v-model:value="form.travelSpeed" :min="50" :max="300" />
            </NFormItem>
            <div class="slicing-form-grid">
              <NFormItem label="Support">
                <NSwitch v-model:value="form.enableSupport" />
              </NFormItem>
              <NFormItem label="Brim Width">
                <NInputNumber v-model:value="form.brimWidth" :min="0" :max="20" :step="0.5" />
              </NFormItem>
            </div>
          </NForm>
        </NCard>

        <NCard v-if="project" title="输出" :bordered="false">
          <NDescriptions :column="1">
            <NDescriptionsItem label="Engine">{{ selectedSlicingEngineLabel }}</NDescriptionsItem>
            <NDescriptionsItem label="填充">{{ form.infillMode === 'tpms' ? 'TPMS 梯度填充' : '普通填充' }}</NDescriptionsItem>
            <NDescriptionsItem label="Firmware">Marlin</NDescriptionsItem>
            <NDescriptionsItem label="格式">.gcode</NDescriptionsItem>
            <NDescriptionsItem v-if="intermediateModelFilename" label="TPMS 中间模型">{{ intermediateModelFilename }}</NDescriptionsItem>
            <NDescriptionsItem v-if="gcodeFilename" label="文件">{{ gcodeFilename }}</NDescriptionsItem>
          </NDescriptions>
        </NCard>

        <NCard title="当前配置摘要" :bordered="false" class="slicer-config-summary">
          <div class="slicer-summary-tags">
            <NTag type="success" round>
              {{ form.infillMode === 'tpms' ? 'TPMS 梯度填充' : `普通填充 · ${form.sparseInfillPattern}` }}
            </NTag>
            <NTag round>{{ selectedSlicingEngineLabel }}</NTag>
          </div>
          <p v-if="form.infillMode === 'tpms'">
            {{ form.tpmsType }} · {{ form.tpmsGradientAxis.toUpperCase() }} 梯度 · {{ form.tpmsGradientStart }} → {{ form.tpmsGradientEnd }}
          </p>
          <p v-else>填充密度 {{ form.sparseInfillDensity }}%，层高 {{ form.layerHeight }} mm</p>
          <small>参数会随本次切片任务保存，生成后可在路径预览中检查。</small>
        </NCard>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NCollapse,
  NCollapseItem,
  NDescriptions,
  NDescriptionsItem,
  NForm,
  NFormItem,
  NInputNumber,
  NRadio,
  NRadioGroup,
  NSelect,
  NSlider,
  NSpace,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
} from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { loadAuthToken, normalizeApiError } from '@/api/client'
import {
  createSlicingTaskApi,
  createModelTaskApi,
  getLatestProjectFileApi,
  getProjectApi,
  getSlicerStatusApi,
  listProjectFilesApi,
  selectLatestProjectFileApi,
  type SlicerStatus,
  type UploadedFile,
} from '@/api/workspace'
import GcodeLayerPreview from '@/components/GcodeLayerPreview.vue'
import ModelPreview from '@/components/ModelPreview.vue'
import type { Project } from '@/types/domain'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const uploadedFile = ref<UploadedFile | null>(null)
const savedFiles = ref<UploadedFile[]>([])
const selectedInputFilename = ref<string | null>(null)
const errorMessage = ref('')
const successMessage = ref('')
const slicing = ref(false)
const generatingTpms = ref(false)
const slicerStatus = ref<SlicerStatus | null>(null)
const activePreview = ref<'model' | 'toolpath'>('model')
const gcodeUrl = ref('')
const gcodeFilename = ref('')
const intermediateModelFilename = ref('')
const settingsCollapsed = ref(false)
const workflowStages = [
  { index: 1, label: '模型', description: '选择输入' },
  { index: 2, label: '参数', description: '填充与材料' },
  { index: 3, label: '切片', description: '生成 G-code' },
  { index: 4, label: '预览', description: '检查路径' },
] as const
const currentStage = computed(() => {
  if (gcodeUrl.value) return 4
  if (selectedInputFilename.value) return 2
  return 1
})
const savedFileOptions = computed(() =>
  savedFiles.value.map((file) => ({
    label: `${file.filename} · ${file.fileKind === 'generated_model' ? '平台生成 TPMS' : '本地导入'} (${(file.sizeBytes / 1024 / 1024).toFixed(2)} MB)`,
    value: file.filename,
  })),
)
const selectedInputFile = computed(() =>
  savedFiles.value.find((file) => file.filename === selectedInputFilename.value) ?? null,
)
const selectedInputIsGenerated = computed(() => selectedInputFile.value?.fileKind === 'generated_model')
const form = reactive({
  infillMode: 'standard' as 'standard' | 'tpms',
  slicingEngine: 'orca' as 'orca' | 'vsp',
  layerHeight: 0.2,
  lineWidth: 0.42,
  speed: 60,
  travelSpeed: 150,
  wallLoops: 2,
  topShellLayers: 4,
  bottomShellLayers: 3,
  sparseInfillDensity: 15,
  sparseInfillPattern: 'gyroid',
  enableSupport: false,
  supportType: 'normal(auto)',
  brimWidth: 0,
  nozzleTemperature: 220,
  bedTemperature: 60,
  filamentType: 'PLA',
  tpmsType: 'gyroid' as 'gyroid' | 'schwarz_p' | 'diamond' | 'iwp' | 'neovius' | 'lidinoid',
  // The continuous negative phase is the most robust default for slicing;
  // Sheet and positive phase remain available for research comparisons.
  tpmsStructureType: 'rod_negative' as 'sheet' | 'rod_negative' | 'rod_positive',
  tpmsCellSize: 8,
  tpmsWallThickness: 0.8,
  tpmsLevelSetOffset: 0,
  tpmsGradientTarget: 'density' as 'density' | 'thickness',
  tpmsGradientAxis: 'x' as 'x' | 'y' | 'z' | 'radial',
  tpmsGradientStart: -0.4,
  tpmsGradientEnd: 0.4,
  tpmsGradientCurve: 'linear' as 'linear' | 'smooth' | 'ease_in' | 'ease_out',
  tpmsPhaseX: 0,
  tpmsPhaseY: 0,
  tpmsPhaseZ: 0,
  tpmsInvertField: false,
  tpmsQuality: 'fast' as 'fast' | 'standard' | 'high',
})

const filamentOptions = ['PLA', 'PETG', 'ABS', 'ASA', 'TPU', 'PA-CF'].map((value) => ({
  label: value,
  value,
}))
const slicingEngineOptions = [
  {
    label: 'OrcaSlicer 通用 STL 切片',
    value: 'orca',
  },
  {
    label: 'VSP 自研可变线宽路径（实验）',
    value: 'vsp',
  },
]
const selectedSlicingEngineLabel = computed(() =>
  form.slicingEngine === 'vsp' ? 'VSP 自研路径（实验）' : 'OrcaSlicer',
)

function selectWorkflowStage(stage: number) {
  if (stage === 1) {
    router.push(`/projects/${route.params.id}/upload`)
  } else if (stage === 2 || stage === 3) {
    activePreview.value = 'model'
    settingsCollapsed.value = false
    window.setTimeout(() => {
      if (stage === 3) {
        document.getElementById('slicing-start-button')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      } else {
        document.querySelector('.slicer-side-panel')?.scrollTo({ top: 0, behavior: 'smooth' })
      }
    }, 0)
  } else if (stage === 4 && gcodeUrl.value) {
    activePreview.value = 'toolpath'
    settingsCollapsed.value = true
  } else if (stage === 4) {
    errorMessage.value = '请先点击“开始切片”，生成 G-code 后再查看路径预览'
  }
}
const infillOptions = [
  ['Gyroid', 'gyroid'],
  ['Grid', 'grid'],
  ['Honeycomb', 'honeycomb'],
  ['Cubic', 'cubic'],
  ['Rectilinear', 'rectilinear'],
  ['Triangles', 'triangles'],
].map(([label, value]) => ({ label, value }))
const tpmsTypeOptions = [
  ['Gyroid', 'gyroid'],
  ['Schwarz-P', 'schwarz_p'],
  ['Diamond', 'diamond'],
  ['I-WP', 'iwp'],
  ['Neovius', 'neovius'],
  ['Lidinoid', 'lidinoid'],
].map(([label, value]) => ({ label, value }))
const tpmsStructureOptions = [
  { label: 'Sheet 壳体（薄壁曲面）', value: 'sheet' },
  { label: 'Solid 负相（连续网络）', value: 'rod_negative' },
  { label: 'Solid 正相（实体骨架）', value: 'rod_positive' },
]
const gradientTargetOptions = [
  { label: '密度 / 等值面梯度', value: 'density' },
  { label: '壁厚梯度', value: 'thickness' },
]
const gradientAxisOptions = [
  { label: 'X 方向', value: 'x' },
  { label: 'Y 方向', value: 'y' },
  { label: 'Z 方向', value: 'z' },
  { label: '径向', value: 'radial' },
]
const gradientCurveOptions = [
  { label: '线性', value: 'linear' },
  { label: '平滑', value: 'smooth' },
  { label: '渐入', value: 'ease_in' },
  { label: '渐出', value: 'ease_out' },
]
const tpmsQualityOptions = [
  { label: '快速（平滑预览）', value: 'fast' },
  { label: '标准（更密网格）', value: 'standard' },
  { label: '高质量（最终导出）', value: 'high' },
]
const gradientValueMin = computed(() => form.tpmsGradientTarget === 'thickness' ? 0.2 : -1.5)
const gradientValueMax = computed(() => form.tpmsGradientTarget === 'thickness' ? 6 : 1.5)

async function loadProject() {
  errorMessage.value = ''

  try {
    const projectId = String(route.params.id)
    if (route.query.infill === 'tpms') {
      form.infillMode = 'tpms'
    }
    project.value = await getProjectApi(projectId)
    try {
      savedFiles.value = await listProjectFilesApi(projectId)
      let latestFile: UploadedFile | null = null
      try {
        latestFile = await getLatestProjectFileApi(projectId)
      } catch {
        // A project may not have a current-input pointer yet; use the first
        // available model only as a compatibility fallback.
      }
      uploadedFile.value = latestFile ?? savedFiles.value.find((file) => file.fileKind !== 'gcode') ?? null
      if (!uploadedFile.value) {
        throw new Error('请先在模型导入页上传 STL/OBJ 文件')
      }
      selectedInputFilename.value = uploadedFile.value.filename
      if (selectedInputIsGenerated.value) {
        form.infillMode = 'tpms'
      }
    } catch {
      uploadedFile.value = null
      savedFiles.value = []
      selectedInputFilename.value = null
    }
  } catch (error) {
    project.value = null
    uploadedFile.value = null
    errorMessage.value = normalizeApiError(error).message
  }
}

async function loadSlicerStatus() {
  try {
    slicerStatus.value = await getSlicerStatusApi()
  } catch (error) {
    slicerStatus.value = {
      engine: 'orca',
      available: false,
      executable: null,
      message: normalizeApiError(error).message,
    }
  }
}

function absoluteFileUrl(fileUrl: string) {
  return `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}${fileUrl.replace('/api/v1', '')}`
}

async function createSlicingTask() {
  if (!selectedInputFilename.value) {
    errorMessage.value = '请先在模型上传页上传 STL/OBJ 文件'
    return
  }

  slicing.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const result = await createSlicingTaskApi(String(route.params.id), {
      inputFilename: selectedInputFilename.value,
      slicingEngine: form.slicingEngine,
      layerHeight: form.layerHeight,
      lineWidth: form.lineWidth,
      printSpeed: form.speed,
      travelSpeed: form.travelSpeed,
      wallLoops: form.wallLoops,
      topShellLayers: form.topShellLayers,
      bottomShellLayers: form.bottomShellLayers,
      sparseInfillDensity: form.sparseInfillDensity,
      sparseInfillPattern: form.sparseInfillPattern,
      enableSupport: form.enableSupport,
      supportType: form.supportType,
      brimWidth: form.brimWidth,
      nozzleTemperature: form.nozzleTemperature,
      bedTemperature: form.bedTemperature,
      filamentType: form.filamentType,
      infillMode: form.infillMode,
      tpmsType: form.tpmsType,
      tpmsStructureType: form.tpmsStructureType,
      tpmsCellSize: form.tpmsCellSize,
      tpmsWallThickness: form.tpmsWallThickness,
      tpmsLevelSetOffset: form.tpmsLevelSetOffset,
      tpmsGradientTarget: form.tpmsGradientTarget,
      tpmsGradientAxis: form.tpmsGradientAxis,
      tpmsGradientStart: form.tpmsGradientStart,
      tpmsGradientEnd: form.tpmsGradientEnd,
      tpmsGradientCurve: form.tpmsGradientCurve,
      tpmsPhaseX: form.tpmsPhaseX,
      tpmsPhaseY: form.tpmsPhaseY,
      tpmsPhaseZ: form.tpmsPhaseZ,
      tpmsInvertField: form.tpmsInvertField,
      tpmsQuality: form.tpmsQuality,
    })
    gcodeUrl.value = absoluteFileUrl(result.gcodeUrl)
    gcodeFilename.value = result.gcodeFilename
    intermediateModelFilename.value = result.intermediateModelFilename ?? ''
    activePreview.value = 'toolpath'
    successMessage.value =
      form.slicingEngine === 'vsp'
        ? `VSP 路径生成完成：${result.gcodeFilename}`
        : form.infillMode === 'tpms' && selectedInputIsGenerated.value
          ? `已有 TPMS 模型已直接完成切片：${result.gcodeFilename}`
          : form.infillMode === 'tpms'
          ? `TPMS 模型 ${result.intermediateModelFilename} 已生成，切片完成：${result.gcodeFilename}`
          : `切片完成：${result.gcodeFilename}`
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    slicing.value = false
  }
}

async function createTpmsModel() {
  if (!selectedInputFilename.value) {
    errorMessage.value = '请先在模型导入页上传或选择 STL/OBJ 文件'
    return
  }

  // The model-generation endpoint uses the project’s selected input pointer.
  // Keep that pointer in sync with the model chosen in this workbench before
  // starting generation (the slicing endpoint itself accepts input_filename).
  if (!selectedInputIsGenerated.value) {
    try {
      await selectLatestProjectFileApi(String(route.params.id), selectedInputFilename.value)
    } catch (error) {
      errorMessage.value = normalizeApiError(error).message
      return
    }
  }

  generatingTpms.value = true
  errorMessage.value = ''
  successMessage.value = ''

  const thicknessGradient = form.tpmsGradientTarget === 'thickness'

  try {
    const result = await createModelTaskApi(String(route.params.id), {
      generationDomain: 'boundary',
      boundaryMode: 'auto',
      tpmsType: form.tpmsType,
      structureType: form.tpmsStructureType,
      cellSize: form.tpmsCellSize,
      cellSizeX: form.tpmsCellSize,
      cellSizeY: form.tpmsCellSize,
      cellSizeZ: form.tpmsCellSize,
      cellCountX: 1,
      cellCountY: 1,
      cellCountZ: 1,
      wallThicknessMm: form.tpmsWallThickness,
      levelSetOffset: form.tpmsLevelSetOffset,
      phaseShiftX: form.tpmsPhaseX,
      phaseShiftY: form.tpmsPhaseY,
      phaseShiftZ: form.tpmsPhaseZ,
      gradientAxis: 'none',
      gradientStrength: 0,
      densityGradientMode: thicknessGradient ? 'none' : 'linear',
      densityGradientAxis: thicknessGradient ? 'x' : form.tpmsGradientAxis,
      densityGradientStartOffset: thicknessGradient ? 0 : form.tpmsGradientStart,
      densityGradientEndOffset: thicknessGradient ? 0 : form.tpmsGradientEnd,
      densityGradientCurve: form.tpmsGradientCurve,
      thicknessGradientMode: thicknessGradient ? 'linear' : 'none',
      thicknessGradientAxis: thicknessGradient ? form.tpmsGradientAxis : 'z',
      thicknessGradientStartMm: thicknessGradient ? form.tpmsGradientStart : form.tpmsWallThickness,
      thicknessGradientEndMm: thicknessGradient ? form.tpmsGradientEnd : form.tpmsWallThickness,
      thicknessGradientCurve: form.tpmsGradientCurve,
      densityMode: 'manual',
      targetRelativeDensity: 0.3,
      gyroidTermWeight: 1,
      schwarzCrossWeight: 0,
      diamondNodalWeight: 1,
      iwpSecondHarmonicWeight: 1,
      neoviusProductWeight: 4,
      lidinoidHarmonicWeight: 0.5,
      lidinoidBias: 0.15,
      invertField: form.tpmsInvertField,
      quality: form.tpmsQuality,
    })

    savedFiles.value = await listProjectFilesApi(String(route.params.id))
    uploadedFile.value = savedFiles.value.find((file) => file.filename === result.modelFilename)
      ?? savedFiles.value.find((file) => file.fileKind === 'generated_model')
      ?? null
    selectedInputFilename.value = uploadedFile.value?.filename ?? result.modelFilename
    intermediateModelFilename.value = result.modelFilename
    project.value = await getProjectApi(String(route.params.id))
    activePreview.value = 'model'
    successMessage.value = `TPMS STL 已生成：${result.modelFilename}，现在可以直接开始切片`
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    generatingTpms.value = false
  }
}

function downloadGcode() {
  fetch(gcodeUrl.value, {
    headers: { Authorization: `Bearer ${loadAuthToken()}` },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`G-code 下载失败：${response.status}`)
      }
      return response.blob()
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = gcodeFilename.value || 'output.gcode'
      link.click()
      URL.revokeObjectURL(url)
    })
    .catch((error: unknown) => {
      errorMessage.value = error instanceof Error ? error.message : 'G-code 下载失败'
    })
}

onMounted(() => {
  loadProject()
  loadSlicerStatus()
})
watch(() => route.params.id, loadProject)
watch(() => route.query.infill, (infill) => {
  if (infill === 'tpms') form.infillMode = 'tpms'
})
watch(() => form.infillMode, (mode) => {
  if (mode !== 'standard' || !selectedInputIsGenerated.value) return

  const originalModel = savedFiles.value.find((file) => file.fileKind === 'uploaded_model')
  if (originalModel) {
    selectedInputFilename.value = originalModel.filename
    successMessage.value = `已切回原始模型：${originalModel.filename}，普通填充参数现在会作用于该模型`
  } else {
    form.infillMode = 'tpms'
    errorMessage.value = '当前只有 TPMS 生成模型，请先重新导入原始模型后再使用普通填充'
  }
})
watch(selectedInputFilename, (filename) => {
  uploadedFile.value = savedFiles.value.find((file) => file.filename === filename) ?? null
  if (uploadedFile.value?.fileKind === 'generated_model') {
    form.infillMode = 'tpms'
  }
})
watch(() => form.tpmsGradientTarget, (target) => {
  if (target === 'thickness' && form.tpmsGradientStart < 0.2) {
    form.tpmsGradientStart = 0.6
    form.tpmsGradientEnd = 1.2
  }
  if (target === 'density' && form.tpmsGradientStart > 1.5) {
    form.tpmsGradientStart = -0.4
    form.tpmsGradientEnd = 0.4
  }
})
</script>
