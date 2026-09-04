<template>
  <main class="section demo-page">
    <div class="section-inner page">
      <div class="page-heading demo-heading">
        <div>
          <p class="eyebrow">PUBLIC DEMO</p>
          <h1>在线生成 TPMS 梯度填充</h1>
          <p>无需登录，选择 TPMS 类型和 X/Y/Z 密度梯度，真实生成、预览并下载 STL。</p>
        </div>
        <NTag type="info" round>访客计算 · 不保存</NTag>
      </div>

      <div class="demo-workbench">
        <NCard :bordered="false" class="demo-parameter-card">
          <template #header>
            <div>
              <strong>基础参数</strong>
              <small>提交后由后端真实计算</small>
            </div>
          </template>

          <NForm label-placement="top">
            <NFormItem label="TPMS 类型">
              <NSelect v-model:value="form.type" :options="typeOptions" />
            </NFormItem>

            <div class="demo-form-grid">
              <NFormItem label="晶胞尺寸">
                <NInputNumber
                  v-model:value="form.cellSize"
                  :min="2"
                  :max="30"
                  :step="0.5"
                  :precision="1"
                >
                  <template #suffix>mm</template>
                </NInputNumber>
              </NFormItem>

              <NFormItem label="单轴晶胞数量">
                <NInputNumber v-model:value="form.cellCount" :min="1" :max="3" :step="1" />
              </NFormItem>
            </div>

            <NFormItem label="结构壁厚">
              <NInputNumber
                v-model:value="form.wallThickness"
                :min="0.2"
                :max="maxWallThickness"
                :step="0.1"
                :precision="1"
              >
                <template #suffix>mm</template>
              </NInputNumber>
            </NFormItem>

            <div class="demo-form-grid">
              <NFormItem label="密度梯度方向">
                <NSelect v-model:value="form.gradientAxis" :options="gradientAxisOptions" />
              </NFormItem>
              <NFormItem label="梯度效果">
                <NTag type="success" round>{{ gradientDescription }}</NTag>
              </NFormItem>
            </div>
            <div class="demo-form-grid">
              <NFormItem label="起始密度偏移">
                <NInputNumber v-model:value="form.gradientStartOffset" :min="-1.5" :max="1.5" :step="0.05" :precision="2" />
              </NFormItem>
              <NFormItem label="结束密度偏移">
                <NInputNumber v-model:value="form.gradientEndOffset" :min="-1.5" :max="1.5" :step="0.05" :precision="2" />
              </NFormItem>
            </div>

            <NFormItem label="网格质量">
              <NRadioGroup v-model:value="form.quality">
                <NRadioButton
                  v-for="option in qualityOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </NRadioButton>
              </NRadioGroup>
            </NFormItem>
          </NForm>

          <div class="demo-summary">
            <div>
              <span>总体尺寸</span>
              <strong>{{ totalSize.toFixed(1) }} mm</strong>
            </div>
            <div>
              <span>晶胞总数</span>
              <strong>{{ totalCellCount }}</strong>
            </div>
          </div>

          <NAlert v-if="errorMessage" type="error" class="demo-result-alert">
            {{ errorMessage }}
          </NAlert>

          <NSpace>
            <NButton :disabled="calculating" @click="resetParameters">恢复默认</NButton>
            <NButton type="primary" :loading="calculating" @click="generateModel">
              生成并查看
            </NButton>
            <NButton :disabled="!mesh" @click="downloadModel">下载 STL</NButton>
          </NSpace>

          <NAlert type="info" :bordered="false" class="demo-limit-note">
            访客最多生成 3 × 3 × 3 晶胞。结果只保留在当前浏览器中，下载后即可关闭。
          </NAlert>
        </NCard>

        <section class="demo-preview-card">
          <div class="demo-live-stage">
            <ModelPreview
              :model-data="mesh?.data"
              filename="demo.stl"
              :bed-size="previewBedSize"
              empty-description="设置参数后点击“生成并查看”"
            />
            <div class="demo-preview-badge">
              <small>LIVE MESH</small>
              <strong>{{ preview.name }}</strong>
            </div>
          </div>

          <div class="demo-preview-content">
            <div>
              <p class="eyebrow">{{ preview.label }}</p>
              <h2>{{ preview.name }}</h2>
              <p>{{ preview.description }}</p>
            </div>
            <div class="demo-feature-list">
              <span v-for="feature in preview.features" :key="feature">{{ feature }}</span>
            </div>
          </div>

          <div v-if="mesh" class="demo-mesh-summary">
            <div><span>顶点数</span><strong>{{ mesh.vertexCount.toLocaleString() }}</strong></div>
            <div><span>三角面数</span><strong>{{ mesh.triangleCount.toLocaleString() }}</strong></div>
            <div><span>计算耗时</span><strong>{{ mesh.durationMs }} ms</strong></div>
          </div>

          <NAlert type="default" :bordered="false">
            画面来自本次参数计算得到的真实梯度 TPMS STL，可旋转、缩放和下载；服务器不保存访客结果。
          </NAlert>
        </section>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NForm,
  NFormItem,
  NInputNumber,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NTag,
} from 'naive-ui'

import { normalizeApiError } from '@/api/client'
import {
  generateDemoTpmsApi,
  type DemoQuality,
  type DemoTpmsMesh,
  type DemoTpmsType,
} from '@/api/demo'
import ModelPreview from '@/components/ModelPreview.vue'

interface DemoForm {
  type: DemoTpmsType
  cellSize: number
  cellCount: number
  wallThickness: number
  quality: DemoQuality
  gradientAxis: 'x' | 'y' | 'z'
  gradientStartOffset: number
  gradientEndOffset: number
}

const form = reactive<DemoForm>({
  type: 'gyroid',
  cellSize: 8,
  cellCount: 2,
  wallThickness: 0.8,
  quality: 'fast',
  gradientAxis: 'x',
  gradientStartOffset: -0.35,
  gradientEndOffset: 0.35,
})

const previews: Record<
  DemoTpmsType,
  { name: string; label: string; description: string; features: string[] }
> = {
  gyroid: {
    name: 'Gyroid',
    label: '连续螺旋曲面',
    description: '无直线通道的连续周期曲面，具有流畅的三维连通路径与均匀的空间分布。',
    features: ['连续曲率', '双向连通', '适合轻量化'],
  },
  schwarz_p: {
    name: 'Schwarz-P',
    label: '正交孔隙曲面',
    description: '由三个正交方向的周期曲面构成，孔隙清晰，结构规律且便于观察单元关系。',
    features: ['正交周期', '规则孔隙', '结构直观'],
  },
  diamond: {
    name: 'Diamond',
    label: '四面体连通曲面',
    description: '具有明显的对角连通关系和多方向通道，空间支撑方向丰富。',
    features: ['对角连通', '多向通道', '拓扑紧密'],
  },
  iwp: {
    name: 'I-WP',
    label: '交织窗口曲面',
    description: '由多方向窗口状孔道交织形成，适合观察复杂连通网络。',
    features: ['窗口孔道', '多向交织', '连通丰富'],
  },
  neovius: {
    name: 'Neovius',
    label: '高起伏孔壁曲面',
    description: '孔壁起伏更强，适合探索高比表面积与多峰孔隙形态。',
    features: ['强起伏', '高比表面积', '多峰孔隙'],
  },
  lidinoid: {
    name: 'Lidinoid',
    label: '扭转连通曲面',
    description: '具有明显扭转与旋转连通特征，形态更接近手性通道。',
    features: ['扭转通道', '旋转连通', '形态复杂'],
  },
}

const typeOptions = [
  { label: 'Gyroid', value: 'gyroid' },
  { label: 'Schwarz-P', value: 'schwarz_p' },
  { label: 'Diamond', value: 'diamond' },
  { label: 'I-WP', value: 'iwp' },
  { label: 'Neovius', value: 'neovius' },
  { label: 'Lidinoid', value: 'lidinoid' },
]

const qualityOptions = [
  { label: '快速（平滑预览）', value: 'fast' },
  { label: '标准（更密网格）', value: 'standard' },
]
const gradientAxisOptions = [
  { label: 'X 方向（例：鞋垫前后）', value: 'x' },
  { label: 'Y 方向（左右）', value: 'y' },
  { label: 'Z 方向（上下）', value: 'z' },
]
const gradientDescription = computed(() => `${form.gradientAxis.toUpperCase()} · ${form.gradientStartOffset.toFixed(2)} → ${form.gradientEndOffset.toFixed(2)}`)

const preview = computed(() => previews[form.type])
const totalSize = computed(() => form.cellSize * form.cellCount)
const totalCellCount = computed(() => form.cellCount ** 3)
const maxWallThickness = computed(() => Math.max(0.2, Math.min(4, form.cellSize / 2 - 0.1)))
const previewBedSize = computed(() => Math.max(30, totalSize.value * 1.7))
const calculating = ref(false)
const errorMessage = ref('')
const mesh = ref<DemoTpmsMesh | null>(null)

watch(form, () => {
  mesh.value = null
  errorMessage.value = ''
})

function resetParameters() {
  form.type = 'gyroid'
  form.cellSize = 8
  form.cellCount = 2
  form.wallThickness = 0.8
  form.quality = 'fast'
  form.gradientAxis = 'x'
  form.gradientStartOffset = -0.35
  form.gradientEndOffset = 0.35
}

async function generateModel() {
  calculating.value = true
  errorMessage.value = ''
  mesh.value = null

  try {
    mesh.value = await generateDemoTpmsApi({
      tpmsType: form.type,
      cellSize: form.cellSize,
      cellCount: form.cellCount,
      wallThicknessMm: form.wallThickness,
      quality: form.quality,
      gradientAxis: form.gradientAxis,
      gradientStartOffset: form.gradientStartOffset,
      gradientEndOffset: form.gradientEndOffset,
    })
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    calculating.value = false
  }
}

function downloadModel() {
  if (!mesh.value) return
  const blob = new Blob([mesh.value.data], { type: 'model/stl' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `demo-${form.type}-${form.gradientAxis}-gradient.stl`
  link.click()
  URL.revokeObjectURL(url)
}
</script>
