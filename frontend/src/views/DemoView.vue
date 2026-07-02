<template>
  <main class="section">
    <div class="section-inner page">
      <div class="page-heading">
        <div>
          <p class="eyebrow">PUBLIC DEMO</p>
          <h1>访客 TPMS Demo</h1>
          <p>当前为前端参数与预览骨架，后续会接入真实 TPMS 生成与 Three.js 模型查看器。</p>
        </div>
        <NTag type="info" round>不可保存 / 不可下载</NTag>
      </div>

      <div class="grid-2">
        <NCard title="参数面板" :bordered="false">
          <NForm label-placement="top">
            <NFormItem label="TPMS 类型">
              <NSelect v-model:value="form.type" :options="typeOptions" />
            </NFormItem>
            <NFormItem label="Cell Size">
              <NSlider v-model:value="form.cellSize" :min="2" :max="20" :step="1" />
            </NFormItem>
            <NFormItem label="重复单元 n">
              <NInputNumber v-model:value="form.n" :min="1" :max="12" />
            </NFormItem>
            <NFormItem label="隐式曲面参数 d">
              <NSlider v-model:value="form.d" :min="-1" :max="1" :step="0.05" />
            </NFormItem>
            <NFormItem label="预览质量">
              <NRadioGroup v-model:value="form.quality">
                <NRadioButton v-for="option in qualityOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </NRadioButton>
              </NRadioGroup>
            </NFormItem>
          </NForm>
        </NCard>

        <div class="preview-panel">
          <div class="page" style="width: 100%">
            <div class="tpms-lattice" />
            <NSpace justify="space-between">
              <NText strong>{{ form.type }}</NText>
              <NText depth="3">cell {{ form.cellSize }} / n {{ form.n }} / d {{ form.d }}</NText>
            </NSpace>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import {
  NCard,
  NForm,
  NFormItem,
  NInputNumber,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSlider,
  NSpace,
  NTag,
  NText,
} from 'naive-ui'

const form = reactive({
  type: 'Gyroid',
  cellSize: 8,
  n: 4,
  d: 0,
  quality: 'standard',
})

const typeOptions = ['Schwarz-P', 'Gyroid', 'Diamond'].map((value) => ({ label: value, value }))
const qualityOptions = [
  { label: '快速', value: 'fast' },
  { label: '标准', value: 'standard' },
  { label: '高质量', value: 'high' },
]
</script>
