<template>
  <section class="page project-tpms-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">TPMS GENERATION</p>
        <h1>TPMS 填充生成</h1>
        <p>面向项目 {{ project?.name ?? route.params.id }} 生成真实 TPMS STL 模型。</p>
      </div>
      <NSpace>
        <NButton @click="router.push(`/projects/${route.params.id}`)">返回项目</NButton>
        <NButton v-if="generation" @click="downloadGeneratedModel">下载 TPMS STL</NButton>
        <NButton v-if="generation" type="primary" @click="router.push(`/projects/${route.params.id}/slicing`)">继续切片</NButton>
      </NSpace>
    </div>

    <NAlert v-if="errorMessage" type="error" :title="errorMessage" />

    <div class="project-tpms-grid">
      <NCard :bordered="false" class="project-tpms-card">
        <div class="tpms-panel-heading">
          <div>
            <span>PARAMETER STACK</span>
            <strong>生成参数</strong>
          </div>
          <small>{{ totalCellCount }} cells · {{ dimensionsText }}</small>
        </div>

        <NForm label-placement="top">
          <section class="tpms-simple-form">
            <div class="tpms-section-title">
              <span>DEMO PARAMETERS</span>
              <strong>基础 TPMS 填充</strong>
            </div>
            <NAlert type="info" :bordered="false">
              默认在当前模型边界内生成。快速模式会先给出平滑预览；需要更密网格时再切换标准或高质量。
            </NAlert>
            <div class="demo-form-grid">
              <NFormItem label="TPMS 类型">
                <NSelect v-model:value="form.tpmsType" :options="typeOptions" />
              </NFormItem>
              <NFormItem label="结构模式">
                <NSelect v-model:value="form.structureType" :options="simpleStructureOptions" />
              </NFormItem>
            </div>
            <div class="demo-form-grid">
              <NFormItem label="晶胞尺寸">
                <NInputNumber v-model:value="form.cellSize" :min="2" :max="30" :step="0.5" :precision="1">
                  <template #suffix>mm</template>
                </NInputNumber>
              </NFormItem>
              <NFormItem :label="form.structureType === 'sheet' ? '结构壁厚' : '等值面偏移'">
                <NInputNumber
                  v-if="form.structureType === 'sheet'"
                  v-model:value="form.wallThicknessMm"
                  :min="0.2"
                  :max="maxWallThickness"
                  :step="0.1"
                  :precision="1"
                >
                  <template #suffix>mm</template>
                </NInputNumber>
                <NInputNumber v-else v-model:value="form.levelSetOffset" :min="-1.5" :max="1.5" :step="0.05" :precision="2" />
              </NFormItem>
            </div>
            <div class="demo-form-grid">
              <NFormItem label="密度梯度方向">
                <NSelect v-model:value="form.densityGradientAxis" :options="simpleGradientAxisOptions" />
              </NFormItem>
              <NFormItem label="生成质量">
                <NSelect v-model:value="form.quality" :options="qualityOptions" />
              </NFormItem>
            </div>
            <div class="demo-form-grid">
              <NFormItem label="起始密度偏移">
                <NInputNumber v-model:value="form.densityGradientStartOffset" :min="-1.5" :max="1.5" :step="0.05" :precision="2" />
              </NFormItem>
              <NFormItem label="结束密度偏移">
                <NInputNumber v-model:value="form.densityGradientEndOffset" :min="-1.5" :max="1.5" :step="0.05" :precision="2" />
              </NFormItem>
            </div>
          </section>

          <NCollapse class="tpms-advanced-collapse">
            <NCollapseItem title="高级参数（可选）" name="advanced">
              <NTabs class="tpms-tabs" type="segment" animated>
                <NTabPane name="basic" tab="基础结构">
                  <div class="tpms-tab-panel">
                    <NFormItem label="生成范围">
                      <NSelect v-model:value="form.generationDomain" :options="generationDomainOptions" />
                    </NFormItem>
                    <NAlert
                      v-if="form.generationDomain === 'boundary'"
                      type="info"
                      title="按当前上传模型边界生成"
                    >
                      系统会在当前选中的 STL/OBJ 内生成 TPMS；封闭实体走 3D 内部判断，鞋垫薄片可用投影轮廓模式。
                    </NAlert>
                    <NFormItem v-if="form.generationDomain === 'boundary'" label="边界处理方式">
                      <NSelect v-model:value="form.boundaryMode" :options="boundaryModeOptions" />
                    </NFormItem>
                    <NFormItem label="TPMS 类型">
                      <NSelect v-model:value="form.tpmsType" :options="typeOptions" />
                    </NFormItem>
                    <NFormItem label="结构模式">
                      <NRadioGroup v-model:value="form.structureType" class="tpms-structure-choice">
                        <NRadio
                          v-for="option in structureOptions"
                          :key="option.value"
                          class="tpms-structure-option"
                          :value="option.value"
                        >
                          <strong>{{ option.label }}</strong>
                          <span>{{ option.description }}</span>
                        </NRadio>
                      </NRadioGroup>
                    </NFormItem>
                    <p class="tpms-parameter-hint">{{ typeDescription }}</p>
                  </div>
                </NTabPane>

                <NTabPane name="scale" tab="晶胞尺度">
                  <div class="tpms-tab-panel">
                    <div class="demo-form-grid">
                      <NFormItem label="统一晶胞尺寸">
                        <NInputNumber v-model:value="form.cellSize" :min="2" :max="30" :step="0.5" :precision="1">
                          <template #suffix>mm</template>
                        </NInputNumber>
                      </NFormItem>
                      <NFormItem label="结构壁厚">
                        <NInputNumber
                          v-model:value="form.wallThicknessMm"
                          :disabled="form.structureType !== 'sheet'"
                          :min="0.2"
                          :max="maxWallThickness"
                          :step="0.1"
                          :precision="1"
                        >
                          <template #suffix>mm</template>
                        </NInputNumber>
                      </NFormItem>
                    </div>
                    <div class="tpms-axis-matrix">
                      <div class="tpms-axis-label" />
                      <span>X</span>
                      <span>Y</span>
                      <span>Z</span>
                      <div class="tpms-axis-label">尺寸 mm</div>
                      <NInputNumber v-model:value="form.cellSizeX" :min="2" :max="30" :step="0.5" :precision="1" />
                      <NInputNumber v-model:value="form.cellSizeY" :min="2" :max="30" :step="0.5" :precision="1" />
                      <NInputNumber v-model:value="form.cellSizeZ" :min="2" :max="30" :step="0.5" :precision="1" />
                      <div class="tpms-axis-label">数量</div>
                      <NInputNumber v-model:value="form.cellCountX" :min="1" :max="4" :step="1" />
                      <NInputNumber v-model:value="form.cellCountY" :min="1" :max="4" :step="1" />
                      <NInputNumber v-model:value="form.cellCountZ" :min="1" :max="4" :step="1" />
                    </div>
                  </div>
                </NTabPane>

                <NTabPane name="density" tab="密度控制">
                  <div class="tpms-tab-panel">
                    <div class="demo-form-grid">
                      <NFormItem label="密度模式">
                        <NSelect v-model:value="form.densityMode" :options="densityModeOptions" />
                      </NFormItem>
                      <NFormItem label="目标相对密度">
                        <NInputNumber
                          v-model:value="form.targetRelativeDensity"
                          :disabled="form.structureType === 'sheet' || form.densityMode === 'manual'"
                          :min="0.03"
                          :max="0.95"
                          :step="0.01"
                          :precision="2"
                        />
                      </NFormItem>
                    </div>
                    <NFormItem label="等值面偏移">
                      <NSlider
                        v-model:value="form.levelSetOffset"
                        :disabled="form.densityMode === 'target'"
                        :min="-1.5"
                        :max="1.5"
                        :step="0.05"
                      />
                      <div class="tpms-inline-value">{{ form.levelSetOffset.toFixed(2) }}</div>
                    </NFormItem>
                  </div>
                </NTabPane>

                <NTabPane name="type-specific" tab="类型专属">
                  <div class="tpms-tab-panel">
                    <p class="tpms-parameter-hint">{{ activeTypeParameterHelp }}</p>

                    <template v-if="form.tpmsType === 'gyroid'">
                      <NFormItem label="螺旋项权重">
                        <NSlider v-model:value="form.gyroidTermWeight" :min="0.2" :max="2" :step="0.05" />
                        <div class="tpms-inline-value">{{ form.gyroidTermWeight.toFixed(2) }}</div>
                      </NFormItem>
                    </template>

                    <template v-else-if="form.tpmsType === 'schwarz_p'">
                      <NFormItem label="交叉项权重">
                        <NSlider v-model:value="form.schwarzCrossWeight" :min="-1" :max="1" :step="0.05" />
                        <div class="tpms-inline-value">{{ form.schwarzCrossWeight.toFixed(2) }}</div>
                      </NFormItem>
                    </template>

                    <template v-else-if="form.tpmsType === 'diamond'">
                      <NFormItem label="节点连通权重">
                        <NSlider v-model:value="form.diamondNodalWeight" :min="0.2" :max="2" :step="0.05" />
                        <div class="tpms-inline-value">{{ form.diamondNodalWeight.toFixed(2) }}</div>
                      </NFormItem>
                    </template>

                    <template v-else-if="form.tpmsType === 'iwp'">
                      <NFormItem label="二次谐波权重">
                        <NSlider v-model:value="form.iwpSecondHarmonicWeight" :min="0.2" :max="2" :step="0.05" />
                        <div class="tpms-inline-value">{{ form.iwpSecondHarmonicWeight.toFixed(2) }}</div>
                      </NFormItem>
                    </template>

                    <template v-else-if="form.tpmsType === 'neovius'">
                      <NFormItem label="三向乘积权重">
                        <NSlider v-model:value="form.neoviusProductWeight" :min="1" :max="8" :step="0.1" />
                        <div class="tpms-inline-value">{{ form.neoviusProductWeight.toFixed(1) }}</div>
                      </NFormItem>
                    </template>

                    <template v-else>
                      <div class="demo-form-grid">
                        <NFormItem label="谐波平衡权重">
                          <NSlider v-model:value="form.lidinoidHarmonicWeight" :min="0.1" :max="1.2" :step="0.05" />
                          <div class="tpms-inline-value">{{ form.lidinoidHarmonicWeight.toFixed(2) }}</div>
                        </NFormItem>
                        <NFormItem label="形态偏置">
                          <NSlider v-model:value="form.lidinoidBias" :min="-0.6" :max="0.6" :step="0.05" />
                          <div class="tpms-inline-value">{{ form.lidinoidBias.toFixed(2) }}</div>
                        </NFormItem>
                      </div>
                    </template>
                  </div>
                </NTabPane>

                <NTabPane name="modulation" tab="空间场梯度 DR">
                  <div class="tpms-tab-panel">
                    <div class="tpms-axis-matrix">
                      <div class="tpms-axis-label" />
                      <span>X</span>
                      <span>Y</span>
                      <span>Z</span>
                      <div class="tpms-axis-label">相位 rad</div>
                      <NInputNumber v-model:value="form.phaseShiftX" :min="-3.14" :max="3.14" :step="0.1" :precision="2" />
                      <NInputNumber v-model:value="form.phaseShiftY" :min="-3.14" :max="3.14" :step="0.1" :precision="2" />
                      <NInputNumber v-model:value="form.phaseShiftZ" :min="-3.14" :max="3.14" :step="0.1" :precision="2" />
                    </div>
                    <NFormItem label="等值面偏移梯度">
                      <NSelect v-model:value="form.densityGradientMode" :options="densityGradientModeOptions" />
                    </NFormItem>
                    <div class="demo-form-grid">
                      <NFormItem label="梯度方向">
                        <NSelect
                          v-model:value="form.densityGradientAxis"
                          :disabled="form.densityGradientMode === 'none'"
                          :options="densityGradientAxisOptions"
                        />
                      </NFormItem>
                      <NFormItem label="过渡曲线">
                        <NSelect
                          v-model:value="form.densityGradientCurve"
                          :disabled="form.densityGradientMode === 'none'"
                          :options="densityGradientCurveOptions"
                        />
                      </NFormItem>
                    </div>
                    <div class="demo-form-grid">
                      <NFormItem label="起始 offset">
                        <NInputNumber
                          v-model:value="form.densityGradientStartOffset"
                          :disabled="form.densityGradientMode === 'none'"
                          :min="-1.5"
                          :max="1.5"
                          :step="0.05"
                          :precision="2"
                        />
                      </NFormItem>
                      <NFormItem label="结束 offset">
                        <NInputNumber
                          v-model:value="form.densityGradientEndOffset"
                          :disabled="form.densityGradientMode === 'none'"
                          :min="-1.5"
                          :max="1.5"
                          :step="0.05"
                          :precision="2"
                        />
                      </NFormItem>
                    </div>
                    <p class="tpms-parameter-hint">
                      Offset 梯度会移动等值面位置；下面的 d(r) 梯度会直接改变 Sheet 壳体的局部壁厚/带宽。
                    </p>
                    <NFormItem label="d(r) 壁厚梯度">
                      <NSelect
                        v-model:value="form.thicknessGradientMode"
                        :disabled="form.structureType !== 'sheet'"
                        :options="thicknessGradientModeOptions"
                      />
                    </NFormItem>
                    <div class="demo-form-grid">
                      <NFormItem label="d(r) 方向">
                        <NSelect
                          v-model:value="form.thicknessGradientAxis"
                          :disabled="form.structureType !== 'sheet' || form.thicknessGradientMode === 'none'"
                          :options="densityGradientAxisOptions"
                        />
                      </NFormItem>
                      <NFormItem label="d(r) 过渡曲线">
                        <NSelect
                          v-model:value="form.thicknessGradientCurve"
                          :disabled="form.structureType !== 'sheet' || form.thicknessGradientMode === 'none'"
                          :options="densityGradientCurveOptions"
                        />
                      </NFormItem>
                    </div>
                    <div class="demo-form-grid">
                      <NFormItem label="起始壁厚">
                        <NInputNumber
                          v-model:value="form.thicknessGradientStartMm"
                          :disabled="form.structureType !== 'sheet' || form.thicknessGradientMode === 'none'"
                          :min="0.2"
                          :max="maxWallThickness"
                          :step="0.1"
                          :precision="1"
                        >
                          <template #suffix>mm</template>
                        </NInputNumber>
                      </NFormItem>
                      <NFormItem label="结束壁厚">
                        <NInputNumber
                          v-model:value="form.thicknessGradientEndMm"
                          :disabled="form.structureType !== 'sheet' || form.thicknessGradientMode === 'none'"
                          :min="0.2"
                          :max="maxWallThickness"
                          :step="0.1"
                          :precision="1"
                        >
                          <template #suffix>mm</template>
                        </NInputNumber>
                      </NFormItem>
                    </div>
                    <p class="tpms-parameter-hint">
                      d(r) 对应公式 |F(x,y,z)| ≤ d(r)。壁厚越大，局部材料带越宽，相对密度越高。
                    </p>
                  </div>
                </NTabPane>

                <NTabPane name="compute" tab="计算设置">
                  <div class="tpms-tab-panel">
                    <div class="demo-form-grid">
                      <NFormItem label="场函数方向">
                        <NSwitch v-model:value="form.invertField">
                          <template #checked>反相</template>
                          <template #unchecked>默认</template>
                        </NSwitch>
                      </NFormItem>
                      <NFormItem label="网格质量">
                        <NSelect v-model:value="form.quality" :options="qualityOptions" />
                      </NFormItem>
                    </div>
                  </div>
                </NTabPane>
              </NTabs>
            </NCollapseItem>
          </NCollapse>
        </NForm>

        <div class="demo-summary">
          <div>
            <span>总体尺寸</span>
            <strong>{{ dimensionsText }}</strong>
          </div>
          <div>
            <span>晶胞总数</span>
            <strong>{{ totalCellCount }}</strong>
          </div>
        </div>

        <NAlert v-if="form.generationDomain === 'boundary'" type="warning" :bordered="false">
          原始上传模型为临时文件；TPMS 生成成功后将保留生成 STL，并自动清理原始文件。
        </NAlert>

        <NButton type="primary" block :loading="generating" @click="createGeneration">
          {{ generating ? '正在生成平滑预览…' : '生成 TPMS 填充 STL' }}
        </NButton>

        <p class="tpms-parameter-hint">
          Level-set 控制实体比例；d(r) 壁厚场控制 Sheet 局部密度；相位控制周期对齐。
        </p>
      </NCard>

      <section class="project-tpms-preview">
        <div class="tpms-preview-heading">
          <div>
            <span>LIVE DESIGN</span>
            <strong>{{ activeTypeLabel }} · {{ activeStructureLabel }}</strong>
          </div>
          <small>{{ form.quality }}</small>
        </div>

        <div class="tpms-live-summary">
          <div>
            <span>总体尺寸</span>
            <strong>{{ dimensionsText }}</strong>
          </div>
          <div>
            <span>密度控制</span>
            <strong>{{ densitySummary }}</strong>
          </div>
          <div>
            <span>梯度控制</span>
            <strong>{{ gradientSummary }}</strong>
          </div>
          <div>
            <span>相位偏移</span>
            <strong>{{ phaseSummary }}</strong>
          </div>
        </div>

        <NAlert v-if="!generation" type="info" :bordered="false">
          {{ previewSourceLabel }}
        </NAlert>

        <ModelPreview
          :source-url="previewUrl || inputPreviewUrl"
          :filename="generation?.modelFilename || inputPreviewFilename"
          :bed-size="previewBedSize"
          empty-description="生成后显示项目 STL 结果"
        />

        <div v-if="generation" class="demo-mesh-summary project-tpms-summary">
          <div><span>文件</span><strong>{{ generation.modelFilename }}</strong></div>
          <div><span>顶点数</span><strong>{{ generation.vertices.toLocaleString() }}</strong></div>
          <div><span>三角面数</span><strong>{{ generation.triangles.toLocaleString() }}</strong></div>
          <div><span>体积</span><strong>{{ generation.volumeMm3 > 0 ? `${generation.volumeMm3.toLocaleString()} mm³` : '壳面网格' }}</strong></div>
          <div><span>表面积</span><strong>{{ generation.surfaceAreaMm2.toLocaleString() }} mm²</strong></div>
          <div><span>相对密度</span><strong>{{ generation.volumeMm3 > 0 ? `${(generation.relativeDensity * 100).toFixed(1)}%` : '需封闭实体' }}</strong></div>
          <div>
            <span>实际 offset</span><strong>{{ generation.effectiveLevelSetOffset.toFixed(3) }}</strong>
          </div>
        </div>

        <NSpace v-if="generation" class="project-tpms-result-actions">
          <NButton @click="downloadGeneratedModel">下载 STL</NButton>
          <NButton @click="router.push(`/projects/${route.params.id}/files`)">在项目文件中查看</NButton>
          <NButton type="primary" @click="router.push(`/projects/${route.params.id}/slicing`)">使用此模型切片</NButton>
        </NSpace>
      </section>
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
} from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { loadAuthToken, normalizeApiError } from '@/api/client'
import {
  createModelTaskApi,
  getProjectApi,
  listProjectFilesApi,
  type ModelGenerationRun,
  type UploadedFile,
} from '@/api/workspace'
import ModelPreview from '@/components/ModelPreview.vue'
import type { Project } from '@/types/domain'

type TpmsType = 'gyroid' | 'schwarz_p' | 'diamond' | 'iwp' | 'neovius' | 'lidinoid'
type StructureType = 'sheet' | 'rod_negative' | 'rod_positive'
type Quality = 'fast' | 'standard' | 'high'
type DensityMode = 'manual' | 'target'
type DensityGradientMode = 'none' | 'linear'
type DensityGradientAxis = 'x' | 'y' | 'z' | 'radial'
type DensityGradientCurve = 'linear' | 'smooth' | 'ease_in' | 'ease_out'
type GenerationDomain = 'block' | 'boundary'
type BoundaryMode = 'auto' | 'closed' | 'footprint'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const inputPreviewFile = ref<UploadedFile | null>(null)
const errorMessage = ref('')
const generating = ref(false)
const generation = ref<ModelGenerationRun | null>(null)

const form = reactive({
  generationDomain: 'boundary' as GenerationDomain,
  boundaryMode: 'auto' as BoundaryMode,
  tpmsType: 'gyroid' as TpmsType,
  structureType: 'rod_negative' as StructureType,
  cellSize: 8,
  cellSizeX: 8,
  cellSizeY: 8,
  cellSizeZ: 8,
  cellCountX: 2,
  cellCountY: 2,
  cellCountZ: 2,
  wallThicknessMm: 0.8,
  levelSetOffset: 0,
  phaseShiftX: 0,
  phaseShiftY: 0,
  phaseShiftZ: 0,
  gradientAxis: 'none' as const,
  gradientStrength: 0,
  densityGradientMode: 'linear' as DensityGradientMode,
  densityGradientAxis: 'x' as DensityGradientAxis,
  densityGradientStartOffset: -0.25,
  densityGradientEndOffset: 0.25,
  densityGradientCurve: 'linear' as DensityGradientCurve,
  thicknessGradientMode: 'none' as DensityGradientMode,
  thicknessGradientAxis: 'z' as DensityGradientAxis,
  thicknessGradientStartMm: 0.6,
  thicknessGradientEndMm: 1.2,
  thicknessGradientCurve: 'linear' as DensityGradientCurve,
  densityMode: 'manual' as DensityMode,
  targetRelativeDensity: 0.3,
  gyroidTermWeight: 1,
  schwarzCrossWeight: 0,
  diamondNodalWeight: 1,
  iwpSecondHarmonicWeight: 1,
  neoviusProductWeight: 4,
  lidinoidHarmonicWeight: 0.5,
  lidinoidBias: 0.15,
  invertField: false,
  quality: 'fast' as Quality,
})

const generationDomainOptions = [
  { label: '规则晶胞块', value: 'block' },
  { label: '当前上传模型边界', value: 'boundary' },
]

const boundaryModeOptions = [
  { label: '自动：封闭体优先，否则投影轮廓', value: 'auto' },
  { label: '封闭实体：严格 3D 内部', value: 'closed' },
  { label: '投影轮廓：适合鞋垫薄片', value: 'footprint' },
]

const typeOptions = [
  { label: 'Gyroid', value: 'gyroid' },
  { label: 'Schwarz-P', value: 'schwarz_p' },
  { label: 'Diamond', value: 'diamond' },
  { label: 'I-WP', value: 'iwp' },
  { label: 'Neovius', value: 'neovius' },
  { label: 'Lidinoid', value: 'lidinoid' },
]

const structureOptions = [
  { label: 'Sheet 壳体', value: 'sheet', description: '按壁厚生成薄壳结构' },
  { label: 'Solid 负相', value: 'rod_negative', description: '提取隐式场负相实体' },
  { label: 'Solid 正相', value: 'rod_positive', description: '提取隐式场正相实体' },
]
const simpleStructureOptions = [
  { label: 'Solid 负相（连续网络）', value: 'rod_negative' },
  { label: 'Sheet 壳体', value: 'sheet' },
  { label: 'Solid 正相', value: 'rod_positive' },
]

const qualityOptions = [
  { label: '快速（平滑预览，约 2–4 秒）', value: 'fast' },
  { label: '标准（更密网格，约 4–8 秒）', value: 'standard' },
  { label: '高质量（最终导出，耗时更长）', value: 'high' },
]

const densityGradientModeOptions = [
  { label: '关闭', value: 'none' },
  { label: '线性 offset 梯度', value: 'linear' },
]

const thicknessGradientModeOptions = [
  { label: '关闭', value: 'none' },
  { label: '线性 d(r) 壁厚梯度', value: 'linear' },
]

const densityGradientAxisOptions = [
  { label: '沿 X 方向', value: 'x' },
  { label: '沿 Y 方向', value: 'y' },
  { label: '沿 Z 方向', value: 'z' },
  { label: '径向：中心到外侧', value: 'radial' },
]
const simpleGradientAxisOptions = densityGradientAxisOptions.filter((option) => option.value !== 'radial')

const densityGradientCurveOptions = [
  { label: '线性', value: 'linear' },
  { label: '平滑过渡', value: 'smooth' },
  { label: '前段变化慢', value: 'ease_in' },
  { label: '后段变化慢', value: 'ease_out' },
]

const densityModeOptions = computed(() => [
  { label: '手动 offset', value: 'manual' },
  {
    label: form.structureType === 'sheet' ? '目标相对密度（Solid 可用）' : '目标相对密度',
    value: 'target',
    disabled: form.structureType === 'sheet',
  },
])

const typeDescriptions: Record<TpmsType, string> = {
  gyroid: 'Gyroid 连续螺旋通道明显，常用于轻量化和流体连通结构。',
  schwarz_p: 'Schwarz-P 孔隙规则、正交关系清楚，适合观察晶胞阵列与孔道尺度。',
  diamond: 'Diamond 拓扑更紧密，多方向连通更明显，适合支撑方向更丰富的结构。',
  iwp: 'I-WP 具有交织状窗口孔道，适合展示更复杂的多孔连通网络。',
  neovius: 'Neovius 孔壁起伏更强，常用于高比表面积、多峰孔隙形态的结构探索。',
  lidinoid: 'Lidinoid 曲面扭转感更明显，适合观察手性/旋转连通特征。',
}

const typeParameterHelps: Record<TpmsType, string> = {
  gyroid: '调节第三个螺旋项权重，可打破完全均衡的 Gyroid 周期，让通道方向更偏向某一组旋转路径。',
  schwarz_p: '交叉项会让 Schwarz-P 从简单正交孔道向更圆滑/耦合的孔窗过渡。',
  diamond: '节点连通权重会改变 Diamond 节点处的收缩与贯通强度，影响多方向支撑特征。',
  iwp: '二次谐波权重控制 I-WP 窗口孔道的锐度与收缩程度。',
  neovius: '三向乘积权重控制 Neovius 孔壁起伏强度，权重越高，形态对比越强。',
  lidinoid: 'Lidinoid 使用谐波平衡与偏置共同控制扭转通道的形态和开口比例。',
}

const typeDescription = computed(() => typeDescriptions[form.tpmsType])
const activeTypeParameterHelp = computed(() => typeParameterHelps[form.tpmsType])
const activeTypeLabel = computed(() => typeOptions.find((option) => option.value === form.tpmsType)?.label ?? 'TPMS')
const activeStructureLabel = computed(
  () => structureOptions.find((option) => option.value === form.structureType)?.label ?? '结构',
)
const totalCellCount = computed(() => form.cellCountX * form.cellCountY * form.cellCountZ)
const maxWallThickness = computed(() =>
  Math.max(0.2, Math.min(6, Math.min(form.cellSizeX, form.cellSizeY, form.cellSizeZ) / 2 - 0.1)),
)
const dimensionsText = computed(() =>
  `${(form.cellSizeX * form.cellCountX).toFixed(1)} × ${(form.cellSizeY * form.cellCountY).toFixed(1)} × ${(form.cellSizeZ * form.cellCountZ).toFixed(1)} mm`,
)
const previewBedSize = computed(() =>
  Math.max(
    30,
    Math.max(
      form.cellSizeX * form.cellCountX,
      form.cellSizeY * form.cellCountY,
      form.cellSizeZ * form.cellCountZ,
    ) * 1.7,
  ),
)
const previewUrl = computed(() => {
  if (!generation.value) return undefined
  return absoluteFileUrl(generation.value.modelUrl)
})
const inputPreviewUrl = computed(() =>
  inputPreviewFile.value ? absoluteFileUrl(inputPreviewFile.value.fileUrl) : '/models/tpms-basic.stl',
)
const inputPreviewFilename = computed(() => inputPreviewFile.value?.filename ?? 'tpms-basic.stl')
const previewSourceLabel = computed(() => inputPreviewFile.value
  ? `当前显示项目模型：${inputPreviewFile.value.filename}。生成完成后会切换为 TPMS 结果。`
  : '当前显示轻量 Gyroid 基础示例。上传模型后会自动切换为你的模型预览。')
const densitySummary = computed(() => {
  if (form.densityMode === 'target') return `${(form.targetRelativeDensity * 100).toFixed(0)}% target`
  return `offset ${form.levelSetOffset.toFixed(2)}`
})
const gradientSummary = computed(() => {
  const gradients: string[] = []

  if (form.densityGradientMode !== 'none') {
    gradients.push(
      `offset ${form.densityGradientAxis.toUpperCase()} ${form.densityGradientStartOffset.toFixed(2)}→${form.densityGradientEndOffset.toFixed(2)}`,
    )
  }

  if (form.structureType === 'sheet' && form.thicknessGradientMode !== 'none') {
    gradients.push(
      `d(r) ${form.thicknessGradientAxis.toUpperCase()} ${form.thicknessGradientStartMm.toFixed(1)}→${form.thicknessGradientEndMm.toFixed(1)}mm`,
    )
  }

  return gradients.length > 0 ? gradients.join(' · ') : '未启用'
})
const phaseSummary = computed(
  () =>
    `${form.phaseShiftX.toFixed(1)} / ${form.phaseShiftY.toFixed(1)} / ${form.phaseShiftZ.toFixed(1)} rad`,
)

function absoluteFileUrl(fileUrl: string) {
  return `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}${fileUrl.replace('/api/v1', '')}`
}

async function loadProject() {
  errorMessage.value = ''

  try {
    project.value = await getProjectApi(String(route.params.id))
    form.generationDomain = project.value.modelFile ? 'boundary' : 'block'
    try {
      const files = await listProjectFilesApi(String(route.params.id))
      inputPreviewFile.value = files.find((file) => file.fileKind !== 'gcode' && file.filename === project.value?.modelFile)
        ?? files.find((file) => file.fileKind !== 'gcode')
        ?? null
    } catch {
      inputPreviewFile.value = null
    }
  } catch (error) {
    project.value = null
    inputPreviewFile.value = null
    errorMessage.value = normalizeApiError(error).message
  }
}

async function downloadGeneratedModel() {
  if (!generation.value) return
  errorMessage.value = ''
  try {
    const response = await fetch(absoluteFileUrl(generation.value.modelUrl), {
      headers: { Authorization: `Bearer ${loadAuthToken()}` },
    })
    if (!response.ok) throw new Error(`STL 下载失败：${response.status}`)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = generation.value.modelFilename
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'STL 下载失败'
  }
}

async function createGeneration() {
  generating.value = true
  errorMessage.value = ''
  generation.value = null

  try {
    generation.value = await createModelTaskApi(String(route.params.id), form)
    project.value = await getProjectApi(String(route.params.id))
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    generating.value = false
  }
}

onMounted(loadProject)
watch(() => route.params.id, loadProject)
watch(
  () => form.cellSize,
  (cellSize) => {
    form.cellSizeX = cellSize
    form.cellSizeY = cellSize
    form.cellSizeZ = cellSize
  },
)
watch(
  () => form.structureType,
  (structureType) => {
    if (structureType === 'sheet') form.densityMode = 'manual'
    if (structureType !== 'sheet') form.thicknessGradientMode = 'none'
  },
)
</script>
