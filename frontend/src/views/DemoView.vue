<template>
  <main class="section demo-page">
    <div class="section-inner page">
      <div class="page-heading demo-heading">
        <div>
          <p class="eyebrow">PUBLIC DEMO</p>
          <h1>探索 TPMS 结构</h1>
          <p>调整基础参数，了解三类周期曲面的形态与尺寸关系。</p>
        </div>
        <NTag type="info" round>访客预览 · 不保存</NTag>
      </div>

      <div class="demo-workbench">
        <NCard :bordered="false" class="demo-parameter-card">
          <template #header>
            <div>
              <strong>基础参数</strong>
              <small>输入值仅用于尺寸估算</small>
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

              <NFormItem label="晶胞数量">
                <NInputNumber v-model:value="form.cellCount" :min="1" :max="12" :step="1" />
              </NFormItem>
            </div>

            <NFormItem label="结构壁厚">
              <NInputNumber
                v-model:value="form.wallThickness"
                :min="0.2"
                :max="4"
                :step="0.1"
                :precision="1"
              >
                <template #suffix>mm</template>
              </NInputNumber>
            </NFormItem>

            <NFormItem label="预览质量">
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
              <span>预计总体尺寸</span>
              <strong>{{ totalSize.toFixed(1) }} mm</strong>
            </div>
            <div>
              <span>单轴采样点</span>
              <strong>{{ sampleCount }}</strong>
            </div>
          </div>

          <NSpace>
            <NButton @click="resetParameters">恢复默认</NButton>
            <NButton type="primary" @click="router.push('/login')">登录后真实生成</NButton>
          </NSpace>
        </NCard>

        <section class="demo-preview-card">
          <div class="demo-preview-stage">
            <Transition name="demo-preview" mode="out-in">
              <img :key="preview.id" :src="preview.image" :alt="preview.alt">
            </Transition>

            <div class="demo-preview-badge">
              <small>STRUCTURE</small>
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

          <NAlert type="default" :bordered="false">
            此处展示对应类型的高质量示意模型；参数修改只计算尺寸与采样规模，不会在访客模式中重新生成网格。
          </NAlert>
        </section>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
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
import { useRouter } from 'vue-router'

type TpmsType = 'gyroid' | 'schwarz_p' | 'diamond'
type PreviewQuality = 'fast' | 'standard' | 'high'

interface DemoForm {
  type: TpmsType
  cellSize: number
  cellCount: number
  wallThickness: number
  quality: PreviewQuality
}

const router = useRouter()

const form = reactive<DemoForm>({
  type: 'gyroid',
  cellSize: 8,
  cellCount: 3,
  wallThickness: 0.8,
  quality: 'standard',
})

const previews: Record<
  TpmsType,
  {
    id: TpmsType
    name: string
    label: string
    description: string
    features: string[]
    image: string
    alt: string
  }
> = {
  gyroid: {
    id: 'gyroid',
    name: 'Gyroid',
    label: '连续螺旋曲面',
    description: '无直线通道的连续周期曲面，具有流畅的三维连通路径与均匀的空间分布。',
    features: ['连续曲率', '双向连通', '适合轻量化'],
    image: '/images/tpms-demo-gyroid-v1.png',
    alt: 'Gyroid 片状 TPMS 三维结构示意',
  },
  schwarz_p: {
    id: 'schwarz_p',
    name: 'Schwarz-P',
    label: '正交孔隙曲面',
    description: '由三个正交方向的周期曲面构成，孔隙清晰，结构规律且便于观察单元关系。',
    features: ['正交周期', '规则孔隙', '结构直观'],
    image: '/images/tpms-demo-schwarz-p-v1.png',
    alt: 'Schwarz-P 片状 TPMS 三维结构示意',
  },
  diamond: {
    id: 'diamond',
    name: 'Diamond',
    label: '四面体连通曲面',
    description: '具有明显的对角连通关系和多方向通道，曲面拓扑更紧密，空间支撑方向丰富。',
    features: ['对角连通', '多向通道', '拓扑紧密'],
    image: '/images/tpms-demo-diamond-v1.png',
    alt: 'Diamond 片状 TPMS 三维结构示意',
  },
}

const typeOptions = [
  { label: 'Gyroid', value: 'gyroid' },
  { label: 'Schwarz-P', value: 'schwarz_p' },
  { label: 'Diamond', value: 'diamond' },
]

const qualityOptions = [
  { label: '快速', value: 'fast' },
  { label: '标准', value: 'standard' },
  { label: '高质量', value: 'high' },
]

const preview = computed(() => previews[form.type])
const totalSize = computed(() => form.cellSize * form.cellCount)
const sampleCount = computed(() => {
  const pointsPerCell = {
    fast: 16,
    standard: 24,
    high: 32,
  }[form.quality]

  return form.cellCount * pointsPerCell + 1
})

function resetParameters() {
  form.cellSize = 8
  form.cellCount = 3
  form.wallThickness = 0.8
  form.quality = 'standard'
}
</script>
