<template>
  <div class="gcode-preview-shell">
    <div class="gcode-preview-stage">
      <div ref="containerRef" class="model-preview gcode-preview">
        <NSpin v-if="loading" />
        <NEmpty v-else-if="!gcodeUrl" description="切片完成后显示路径预览" />
        <NAlert v-else-if="errorMessage" type="error" :title="errorMessage" />
      </div>

      <aside v-if="layers.length" class="gcode-layer-range" aria-label="层显示范围">
        <div class="gcode-layer-range-heading">
          <span>显示层</span>
          <strong>{{ selectedLayerRange[0] + 1 }} - {{ selectedLayerRange[1] + 1 }}</strong>
        </div>
        <NSlider
          v-model:value="layerRange"
          vertical
          range
          :min="0"
          :max="Math.max(layers.length - 1, 0)"
          :step="1"
          :format-tooltip="formatLayerTooltip"
        />
        <div class="gcode-layer-range-values">
          <span>{{ selectedLowerLayerLabel }}</span>
          <span>{{ layerHeightLabel }}</span>
        </div>
      </aside>
    </div>

    <div class="gcode-preview-controls">
      <div class="gcode-control-row">
        <NText depth="3">
          当前层 {{ currentLayer + 1 }} · 行 {{ currentLayerLineOffset + 1 }} / {{ currentLayerLineCount }}
          <span class="gcode-line-hint">G-code {{ currentLineNumber }}</span>
        </NText>
        <NText depth="3">{{ activeLineMotionLabel }}</NText>
      </div>
      <NSlider
        v-model:value="currentLayerLineOffset"
        :disabled="!activeLayer"
        :min="0"
        :max="Math.max(currentLayerLineCount - 1, 0)"
        :step="1"
      />

      <div v-if="diagnostics.length" class="gcode-diagnostics">
        <span v-for="item in diagnostics" :key="item.label">
          {{ item.label }} {{ item.durationMs.toFixed(0) }}ms
        </span>
      </div>
    </div>

    <div v-if="layers.length" class="gcode-preview-details">
      <div class="gcode-type-list">
        <div v-for="item in typeStats" :key="item.type" class="gcode-type-item">
          <NCheckbox
            :checked="visibleTypes[item.type]"
            :disabled="item.length === 0"
            @update:checked="setTypeVisible(item.type, $event)"
          />
          <span class="gcode-type-swatch" :style="{ background: item.color }" />
          <span>{{ item.label }}</span>
          <strong>{{ item.length.toFixed(2) }} m</strong>
        </div>
      </div>

      <pre ref="codePaneRef" class="gcode-lines" @scroll="handleCodeScroll"><code
        :style="{
          paddingTop: `${virtualTopPadding}px`,
          paddingBottom: `${virtualBottomPadding}px`,
        }"
      ><span
        v-for="line in visibleGcodeLines"
        :key="line.number"
        :data-line="line.number"
        :class="{
          'is-active': line.number === currentLineNumber,
          'is-layer-line': activeLayer && line.number >= activeLayer.startLine && line.number <= activeLayer.endLine,
        }"
      ><span class="gcode-line-number">{{ line.number }}</span>{{ line.text }}
</span></code></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { NAlert, NCheckbox, NEmpty, NSlider, NSpin, NText } from 'naive-ui'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

import { loadAuthToken } from '@/api/client'
import { getSegmentDrawRange, lowerBound } from '@/gcode/lineRange'

type SegmentType =
  | 'innerWall'
  | 'outerWall'
  | 'infill'
  | 'solidInfill'
  | 'topSurface'
  | 'bottomSurface'
  | 'support'
  | 'travel'
  | 'other'

interface Segment {
  start: RawPoint
  end: RawPoint
  z: number
  lineNumber: number
  raw: string
  type: SegmentType
  length: number
}

interface Layer {
  index: number
  startLine: number
  endLine: number
  z: number | null
  height: number | null
}

interface RawPoint {
  x: number
  y: number
  z: number
}

interface RawLayer {
  index: number
  startLine: number
  endLine: number
  z: number | null
  height: number | null
}

interface RawParsedGcode {
  lines: string[]
  layers: RawLayer[]
  batches: TransferBatch[]
}

interface TransferBatch {
  type: SegmentType
  positions: Float32Array
  lineNumbers: Uint32Array
  zValues: Float32Array
  lengths: Float32Array
}

interface ObjectParsedGcode {
  lines: string[]
  layers: ObjectLayer[]
  segments: Segment[]
}

interface ObjectLayer extends Layer {
  segments: Segment[]
}

interface ParserState {
  position: { x: number; y: number; z: number; e: number }
  currentType: SegmentType
  relativeExtrusion: boolean
  relativePositioning: boolean
}

interface PathBatch {
  type: SegmentType
  line: THREE.LineSegments
  lineNumbers: Uint32Array
  zValues: Float32Array
  lengths: Float32Array
}

interface DiagnosticItem {
  label: string
  durationMs: number
}

const GCODE_NUMBER = '[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?'

interface WorkerParseResult {
  payload: RawParsedGcode
  workerParseDurationMs: number | null
  roundTripDurationMs: number
}

const props = withDefaults(
  defineProps<{
    gcodeUrl?: string
    bedSize?: number
  }>(),
  {
    gcodeUrl: undefined,
    bedSize: 250,
  },
)

const typeMeta: Record<SegmentType, { label: string; color: string }> = {
  outerWall: { label: '外墙', color: '#ff8a1c' },
  innerWall: { label: '内墙', color: '#ffe14a' },
  infill: { label: '稀疏填充', color: '#e3342f' },
  solidInfill: { label: '内部实心填充', color: '#a855f7' },
  topSurface: { label: '顶面', color: '#ff4f70' },
  bottomSurface: { label: '底面', color: '#38bdf8' },
  support: { label: '支撑', color: '#22c55e' },
  travel: { label: '空驶', color: '#94a3b8' },
  other: { label: '其他', color: '#f8fafc' },
}

const CODE_LINE_HEIGHT = 19
const CODE_OVERSCAN = 32

const containerRef = ref<HTMLDivElement | null>(null)
const codePaneRef = ref<HTMLPreElement | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const layers = ref<Layer[]>([])
const gcodeLines = ref<string[]>([])
const transferBatches = ref<TransferBatch[]>([])
const currentLayer = ref(0)
const currentLayerLineOffset = ref(0)
const layerRange = ref<[number, number]>([0, 0])
const visibleTypes = ref<Record<SegmentType, boolean>>({
  innerWall: true,
  outerWall: true,
  infill: true,
  solidInfill: true,
  topSurface: true,
  bottomSurface: true,
  support: true,
  travel: false,
  other: true,
})
const codeScrollTop = ref(0)
const codeViewportHeight = ref(210)
const diagnostics = ref<DiagnosticItem[]>([])

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let resizeObserver: ResizeObserver | null = null
let animationFrame = 0
let pathGroup: THREE.Group | null = null
let activeLineGroup: THREE.Group | null = null
let pathBatches = new Map<SegmentType, PathBatch>()
let lastBufferBuildDurationMs = 0

const activeLayer = computed(() => layers.value[currentLayer.value] ?? null)

const selectedLayerRange = computed<[number, number]>(() => {
  const upperLimit = Math.max(layers.value.length - 1, 0)
  const first = Math.min(Math.max(Math.round(layerRange.value[0] ?? 0), 0), upperLimit)
  const second = Math.min(Math.max(Math.round(layerRange.value[1] ?? first), 0), upperLimit)
  return first <= second ? [first, second] : [second, first]
})

const selectedLowerLayer = computed(() => layers.value[selectedLayerRange.value[0]] ?? null)

const currentLayerLineCount = computed(() => {
  const layer = activeLayer.value
  return layer ? Math.max(layer.endLine - layer.startLine + 1, 1) : 1
})

const currentLineNumber = computed(() => {
  const layer = activeLayer.value
  if (!layer) return 1
  return Math.min(layer.startLine + currentLayerLineOffset.value, layer.endLine)
})

const activeLineSegment = computed(() => {
  const lineNumber = currentLineNumber.value
  for (const batch of pathBatches.values()) {
    const start = lowerBound(batch.lineNumbers, lineNumber)
    if (batch.lineNumbers[start] === lineNumber) {
      return {
        type: batch.type,
        z: batch.zValues[start],
      }
    }
  }
  return null
})

const layerHeightLabel = computed(() => {
  const layer = activeLayer.value
  if (!layer) return 'Z 0.00 mm'
  const z = layer.z === null ? '-' : `${layer.z.toFixed(2)} mm`
  const height = layer.height === null ? '-' : `${layer.height.toFixed(2)} mm`
  return `Z ${z} / 层高 ${height}`
})

const selectedLowerLayerLabel = computed(() => {
  const layer = selectedLowerLayer.value
  if (!layer) return '起始层 -'
  return `起始 Z ${layer.z === null ? '-' : `${layer.z.toFixed(2)} mm`}`
})

const activeLineMotionLabel = computed(() => {
  const segment = activeLineSegment.value
  if (!segment) return '非路径指令'
  return `${typeMeta[segment.type].label} / Z ${segment.z.toFixed(2)}`
})

const firstVisibleCodeIndex = computed(() => {
  return Math.max(Math.floor(codeScrollTop.value / CODE_LINE_HEIGHT) - CODE_OVERSCAN, 0)
})

const visibleCodeLineCount = computed(() => {
  return Math.ceil(codeViewportHeight.value / CODE_LINE_HEIGHT) + CODE_OVERSCAN * 2
})

const visibleGcodeLines = computed(() => {
  const start = firstVisibleCodeIndex.value
  return gcodeLines.value.slice(start, start + visibleCodeLineCount.value).map((text, index) => ({
    number: start + index + 1,
    text,
  }))
})

const virtualTopPadding = computed(() => firstVisibleCodeIndex.value * CODE_LINE_HEIGHT)

const virtualBottomPadding = computed(() => {
  const hiddenLines = Math.max(gcodeLines.value.length - firstVisibleCodeIndex.value - visibleGcodeLines.value.length, 0)
  return hiddenLines * CODE_LINE_HEIGHT
})

const typeStats = computed(() => {
  return transferBatches.value
    .map((batch) => ({
      type: batch.type,
      length: batch.lengths.reduce((total, length) => total + length, 0),
    }))
    .map(({ type, length }) => ({
      type,
      label: typeMeta[type].label,
      color: typeMeta[type].color,
      length: length / 1000,
    }))
    .sort((a, b) => b.length - a.length)
})

function disposeObject(object: THREE.Object3D) {
  object.traverse((child) => {
    if (child instanceof THREE.LineSegments || child instanceof THREE.Line || child instanceof THREE.Mesh) {
      child.geometry.dispose()
      if (Array.isArray(child.material)) {
        child.material.forEach((material) => material.dispose())
      } else {
        child.material.dispose()
      }
    }
  })
}

function disposeScene() {
  cancelAnimationFrame(animationFrame)
  resizeObserver?.disconnect()
  resizeObserver = null
  controls?.dispose()
  controls = null

  if (scene) {
    scene.children.forEach(disposeObject)
  }

  if (renderer && containerRef.value?.contains(renderer.domElement)) {
    containerRef.value.removeChild(renderer.domElement)
  }

  renderer?.dispose()
  renderer = null
  scene = null
  camera = null
  pathGroup = null
  activeLineGroup = null
  pathBatches = new Map<SegmentType, PathBatch>()
}

function parseCoordinate(line: string, axis: 'X' | 'Y' | 'Z' | 'E') {
  const match = line.match(new RegExp(`${axis}(${GCODE_NUMBER})`, 'i'))
  return match ? Number(match[1]) : undefined
}

function parseArcOffset(line: string, axis: 'I' | 'J' | 'R') {
  const match = line.match(new RegExp(`${axis}(${GCODE_NUMBER})`, 'i'))
  return match ? Number(match[1]) : undefined
}

function parseCommentNumber(line: string, key: 'Z' | 'HEIGHT') {
  const match = line.match(new RegExp(`^;${key}:\\s*(${GCODE_NUMBER})`, 'i'))
  return match ? Number(match[1]) : null
}

function parseSegmentType(line: string, currentType: SegmentType) {
  const normalized = line.toLowerCase()
  if (!normalized.startsWith(';')) return currentType

  const feature = normalized
    .replace(/^;\s*/, '')
    .replace(/^(type|feature|extrusion role)\s*:\s*/, '')
    .trim()

  if (feature.includes('outer wall') || feature.includes('external perimeter')) return 'outerWall'
  if (feature.includes('overhang wall') || feature.includes('bridge')) return 'outerWall'
  if (feature.includes('inner wall') || feature.includes('internal perimeter')) return 'innerWall'
  if (feature.includes('sparse infill') || feature.includes('internal infill')) return 'infill'
  if (feature.includes('gap fill')) return 'solidInfill'
  if (feature.includes('solid infill') || feature.includes('internal solid')) return 'solidInfill'
  if (feature.includes('top surface') || feature.includes('top solid') || feature.includes('ironing')) return 'topSurface'
  if (feature.includes('bottom surface') || feature.includes('bottom solid')) return 'bottomSurface'
  if (feature.includes('support')) return 'support'
  if (feature.includes('skirt') || feature.includes('brim')) return 'other'
  if (feature.includes('travel')) return 'travel'
  return currentType
}

function distance(start: RawPoint, end: RawPoint) {
  return Math.hypot(end.x - start.x, end.y - start.y, end.z - start.z)
}

function addSegment(
  targetSegments: Segment[],
  currentLayerData: ObjectLayer | null,
  start: RawPoint,
  end: RawPoint,
  lineNumber: number,
  raw: string,
  type: SegmentType,
) {
  const length = distance(start, end)
  if (length <= 0.001) return

  const segment = {
    start,
    end,
    z: end.z,
    lineNumber,
    raw,
    type,
    length,
  }
  targetSegments.push(segment)
  currentLayerData?.segments.push(segment)
}

function addArcSegments(
  targetSegments: Segment[],
  currentLayerData: ObjectLayer | null,
  start: RawPoint,
  end: RawPoint,
  line: string,
  lineNumber: number,
  raw: string,
  type: SegmentType,
  clockwise: boolean,
) {
  const i = parseArcOffset(line, 'I')
  const j = parseArcOffset(line, 'J')
  const r = parseArcOffset(line, 'R')
  let centerX: number
  let centerY: number

  if (i !== undefined || j !== undefined) {
    centerX = start.x + (i ?? 0)
    centerY = start.y + (j ?? 0)
  } else if (r !== undefined) {
    const dx = end.x - start.x
    const dy = end.y - start.y
    const chord = Math.hypot(dx, dy)
    if (chord <= 0.001 || Math.abs(r) < chord / 2) {
      addSegment(targetSegments, currentLayerData, start, end, lineNumber, raw, type)
      return
    }

    const midpointX = (start.x + end.x) / 2
    const midpointY = (start.y + end.y) / 2
    const height = Math.sqrt(Math.max(r * r - (chord / 2) ** 2, 0))
    const normalX = -dy / chord
    const normalY = dx / chord
    const sign = clockwise === r > 0 ? -1 : 1
    centerX = midpointX + normalX * height * sign
    centerY = midpointY + normalY * height * sign
  } else {
    addSegment(targetSegments, currentLayerData, start, end, lineNumber, raw, type)
    return
  }

  const radius = Math.hypot(start.x - centerX, start.y - centerY)
  if (radius <= 0.001) {
    addSegment(targetSegments, currentLayerData, start, end, lineNumber, raw, type)
    return
  }

  const startAngle = Math.atan2(start.y - centerY, start.x - centerX)
  let endAngle = Math.atan2(end.y - centerY, end.x - centerX)
  if (clockwise && endAngle >= startAngle) endAngle -= Math.PI * 2
  if (!clockwise && endAngle <= startAngle) endAngle += Math.PI * 2

  const sweep = endAngle - startAngle
  const steps = Math.max(8, Math.ceil((Math.abs(sweep) * radius) / 1.5))
  let previous = start

  for (let step = 1; step <= steps; step += 1) {
    const progress = step / steps
    const angle = startAngle + sweep * progress
    const point = {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
      z: start.z + (end.z - start.z) * progress,
    }
    addSegment(targetSegments, currentLayerData, previous, point, lineNumber, raw, type)
    previous = point
  }
}

function createLayer(lineNumber: number, parsedLayers: ObjectLayer[]) {
  const layer: ObjectLayer = {
    index: parsedLayers.length,
    startLine: lineNumber,
    endLine: lineNumber,
    z: null,
    height: null,
    segments: [],
  }
  parsedLayers.push(layer)
  return layer
}

function updateModalState(line: string, state: ParserState) {
  if (/^M83\b/i.test(line)) {
    state.relativeExtrusion = true
    return true
  }
  if (/^M82\b/i.test(line)) {
    state.relativeExtrusion = false
    return true
  }
  if (/^G91\b/i.test(line)) {
    state.relativePositioning = true
    return true
  }
  if (/^G90\b/i.test(line)) {
    state.relativePositioning = false
    return true
  }
  return false
}

function parseMotionLine(
  line: string,
  raw: string,
  lineNumber: number,
  state: ParserState,
  parsedSegments: Segment[],
  currentLayerData: ObjectLayer | null,
) {
  if (/^G92\b/i.test(line)) {
    state.position.x = parseCoordinate(line, 'X') ?? state.position.x
    state.position.y = parseCoordinate(line, 'Y') ?? state.position.y
    state.position.z = parseCoordinate(line, 'Z') ?? state.position.z
    state.position.e = parseCoordinate(line, 'E') ?? state.position.e
    return
  }

  const command = line.match(/^G([0-3])\b/i)?.[1]
  if (!command) return

  const rawX = parseCoordinate(line, 'X')
  const rawY = parseCoordinate(line, 'Y')
  const rawZ = parseCoordinate(line, 'Z')
  const rawE = parseCoordinate(line, 'E')
  const next = {
    x: rawX === undefined ? state.position.x : state.relativePositioning ? state.position.x + rawX : rawX,
    y: rawY === undefined ? state.position.y : state.relativePositioning ? state.position.y + rawY : rawY,
    z: rawZ === undefined ? state.position.z : state.relativePositioning ? state.position.z + rawZ : rawZ,
    e: rawE,
  }
  const hasXyMove = next.x !== state.position.x || next.y !== state.position.y
  const extrusionDelta =
    next.e === undefined ? 0 : state.relativeExtrusion ? next.e : next.e - state.position.e

  if (hasXyMove) {
    const start = { x: state.position.x, y: state.position.y, z: state.position.z }
    const end = { x: next.x, y: next.y, z: next.z }
    const segmentType = extrusionDelta > 0 ? state.currentType : 'travel'

    if (command === '2' || command === '3') {
      addArcSegments(
        parsedSegments,
        currentLayerData,
        start,
        end,
        line,
        lineNumber,
        raw,
        segmentType,
        command === '2',
      )
    } else {
      addSegment(parsedSegments, currentLayerData, start, end, lineNumber, raw, segmentType)
    }
  }

  state.position.x = next.x
  state.position.y = next.y
  state.position.z = next.z
  state.position.e = next.e ?? state.position.e
}

function parseGcode(gcode: string) {
  const rawLines = gcode.split(/\r?\n/)
  const parsedLayers: ObjectLayer[] = []
  const parsedSegments: Segment[] = []
  const state: ParserState = {
    position: { x: 0, y: 0, z: 0, e: 0 },
    currentType: 'other',
    relativeExtrusion: false,
    relativePositioning: false,
  }
  let currentLayerData: ObjectLayer | null = null

  rawLines.forEach((rawLine, index) => {
    const lineNumber = index + 1
    const trimmedRaw = rawLine.trim()

    if (/^;LAYER_CHANGE\b/i.test(trimmedRaw)) {
      if (currentLayerData) {
        currentLayerData.endLine = lineNumber - 1
      }
      currentLayerData = createLayer(lineNumber, parsedLayers)
    } else if (currentLayerData) {
      const z = parseCommentNumber(trimmedRaw, 'Z')
      const height = parseCommentNumber(trimmedRaw, 'HEIGHT')
      if (z !== null) currentLayerData.z = z
      if (height !== null) currentLayerData.height = height
    }

    state.currentType = parseSegmentType(trimmedRaw, state.currentType)

    const line = rawLine.split(';')[0]?.trim()
    if (!line) return
    if (updateModalState(line, state)) return

    parseMotionLine(line, trimmedRaw, lineNumber, state, parsedSegments, currentLayerData)
  })

  if (parsedLayers.length > 0) {
    parsedLayers[parsedLayers.length - 1].endLine = rawLines.length
  }

  return {
    lines: rawLines,
    layers: parsedLayers,
    segments: parsedSegments,
  }
}

function objectParsedToTransfer(parsed: ObjectParsedGcode): RawParsedGcode {
  const grouped = new Map<SegmentType, Segment[]>()
  for (const segment of parsed.segments) {
    const segments = grouped.get(segment.type)
    if (segments) segments.push(segment)
    else grouped.set(segment.type, [segment])
  }

  const batches = [...grouped.entries()].map(([type, groupedSegments]) => {
    const positions = new Float32Array(groupedSegments.length * 6)
    const lineNumbers = new Uint32Array(groupedSegments.length)
    const zValues = new Float32Array(groupedSegments.length)
    const lengths = new Float32Array(groupedSegments.length)

    groupedSegments.forEach((segment, index) => {
      const positionIndex = index * 6
      positions[positionIndex] = segment.start.x
      positions[positionIndex + 1] = segment.start.y
      positions[positionIndex + 2] = segment.start.z + 0.04
      positions[positionIndex + 3] = segment.end.x
      positions[positionIndex + 4] = segment.end.y
      positions[positionIndex + 5] = segment.end.z + 0.04
      lineNumbers[index] = segment.lineNumber
      zValues[index] = segment.z
      lengths[index] = segment.length
    })

    return { type, positions, lineNumbers, zValues, lengths }
  })

  return {
    lines: parsed.lines,
    layers: parsed.layers.map(({ index, startLine, endLine, z, height }) => ({
      index,
      startLine,
      endLine,
      z,
      height,
    })),
    batches,
  }
}

function parseGcodeInWorker(gcode: string) {
  return new Promise<WorkerParseResult>((resolve, reject) => {
    const startedAt = performance.now()
    const worker = new Worker(new URL('../workers/gcodeParser.worker.ts', import.meta.url), {
      type: 'module',
    })

    worker.onmessage = (
      event: MessageEvent<{
        ok: boolean
        payload?: RawParsedGcode
        error?: string
        parseDurationMs?: number
      }>,
    ) => {
      worker.terminate()
      if (event.data.ok && event.data.payload) {
        resolve({
          payload: event.data.payload,
          workerParseDurationMs: event.data.parseDurationMs ?? null,
          roundTripDurationMs: performance.now() - startedAt,
        })
      } else {
        reject(new Error(event.data.error ?? 'G-code 解析失败'))
      }
    }
    worker.onerror = (event) => {
      worker.terminate()
      reject(new Error(event.message || 'G-code worker failed'))
    }
    worker.postMessage({ gcode })
  })
}

function createBed(size: number) {
  const group = new THREE.Group()
  group.position.set(size / 2, size / 2, 0)

  const bed = new THREE.Mesh(
    new THREE.PlaneGeometry(size, size),
    new THREE.MeshStandardMaterial({
      color: '#41484b',
      roughness: 0.88,
      side: THREE.DoubleSide,
    }),
  )
  bed.position.z = -0.04
  group.add(bed)

  const grid = new THREE.GridHelper(size, 20, '#a8b0b4', '#656d71')
  grid.rotation.x = Math.PI / 2
  group.add(grid)

  const border = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.PlaneGeometry(size, size)),
    new THREE.LineBasicMaterial({ color: '#eef3f7' }),
  )
  group.add(border)
  return group
}

function initScene() {
  const container = containerRef.value
  if (!container) return

  disposeScene()
  scene = new THREE.Scene()
  scene.background = new THREE.Color('#303637')
  camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 2000)
  camera.up.set(0, 0, 1)
  camera.position.set(props.bedSize * 0.62, -props.bedSize * 0.82, props.bedSize * 0.62)
  camera.lookAt(props.bedSize / 2, props.bedSize / 2, props.bedSize * 0.12)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setSize(container.clientWidth, container.clientHeight)
  container.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(props.bedSize / 2, props.bedSize / 2, props.bedSize * 0.12)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.maxDistance = props.bedSize * 3
  controls.update()

  scene.add(createBed(props.bedSize))
  pathGroup = new THREE.Group()
  activeLineGroup = new THREE.Group()
  scene.add(pathGroup)
  scene.add(activeLineGroup)
  buildPathBatches()

  resizeObserver = new ResizeObserver(() => {
    if (!container || !renderer || !camera) return
    camera.aspect = container.clientWidth / container.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(container.clientWidth, container.clientHeight)
  })
  resizeObserver.observe(container)

  function animate() {
    if (!scene || !camera || !renderer) return
    controls?.update()
    renderer.render(scene, camera)
    animationFrame = requestAnimationFrame(animate)
  }
  animate()
}

function buildLineSegmentsFromPositions(positions: Float32Array, color: string, opacity = 1) {
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  const line = new THREE.LineSegments(
    geometry,
    new THREE.LineBasicMaterial({
      color,
      transparent: opacity < 1,
      opacity,
      // Toolpaths at the same Z plane must not hide one another through depth fighting.
      depthTest: false,
      depthWrite: false,
    }),
  )
  line.frustumCulled = false
  return line
}

function buildPathBatches() {
  if (!pathGroup) return
  const startedAt = performance.now()
  pathGroup.children.forEach(disposeObject)
  pathGroup.clear()
  pathBatches = new Map<SegmentType, PathBatch>()

  for (const batch of transferBatches.value) {
    const line = buildLineSegmentsFromPositions(
      batch.positions,
      typeMeta[batch.type].color,
      batch.type === 'travel' ? 0.26 : 1,
    )
    line.geometry.setDrawRange(0, 0)
    line.visible = visibleTypes.value[batch.type]
    pathGroup.add(line)
    pathBatches.set(batch.type, {
      type: batch.type,
      line,
      lineNumbers: batch.lineNumbers,
      zValues: batch.zValues,
      lengths: batch.lengths,
    })
  }
  lastBufferBuildDurationMs = performance.now() - startedAt
}

function renderActiveLine() {
  if (!activeLineGroup) return
  activeLineGroup.children.forEach(disposeObject)
  activeLineGroup.clear()

  const chunks: Float32Array[] = []
  let totalValues = 0
  for (const batch of pathBatches.values()) {
    if (!visibleTypes.value[batch.type]) continue
    const start = lowerBound(batch.lineNumbers, currentLineNumber.value)
    let end = start
    while (end < batch.lineNumbers.length && batch.lineNumbers[end] === currentLineNumber.value) {
      end += 1
    }
    if (end > start) {
      const chunk = (batch.line.geometry.getAttribute('position').array as Float32Array).slice(
        start * 6,
        end * 6,
      )
      chunks.push(chunk)
      totalValues += chunk.length
    }
  }

  if (totalValues > 0) {
    const positions = new Float32Array(totalValues)
    let offset = 0
    for (const chunk of chunks) {
      positions.set(chunk, offset)
      offset += chunk.length
    }
    activeLineGroup.add(buildLineSegmentsFromPositions(positions, '#00d5c8', 1))
  }
}

function renderLayers() {
  const lowerLayer = selectedLowerLayer.value
  const startLine = lowerLayer?.startLine ?? 1
  const endLine = currentLineNumber.value

  for (const batch of pathBatches.values()) {
    batch.line.visible = visibleTypes.value[batch.type]
    const drawRange = getSegmentDrawRange(batch.lineNumbers, startLine, endLine)
    batch.line.geometry.setDrawRange(drawRange.startVertex, drawRange.vertexCount)
  }
  renderActiveLine()
}

function setTypeVisible(type: SegmentType, enabled: boolean) {
  visibleTypes.value[type] = enabled
}

function formatLayerTooltip(value: number) {
  const layer = layers.value[Math.round(value)]
  if (!layer) return `层 ${Math.round(value) + 1}`
  const z = layer.z === null ? '-' : layer.z.toFixed(2)
  return `层 ${layer.index + 1} · Z ${z} mm`
}

function handleCodeScroll() {
  const codePane = codePaneRef.value
  if (!codePane) return
  codeScrollTop.value = codePane.scrollTop
  codeViewportHeight.value = codePane.clientHeight
}

function scrollCodeToCurrentLine() {
  const codePane = codePaneRef.value
  if (!codePane) return

  nextTick(() => {
    const targetTop =
      (currentLineNumber.value - 1) * CODE_LINE_HEIGHT - codePane.clientHeight / 2 + CODE_LINE_HEIGHT / 2
    codePane.scrollTop = Math.max(targetTop, 0)
    handleCodeScroll()
  })
}

async function loadGcode() {
  if (!props.gcodeUrl) {
    disposeScene()
    layers.value = []
    gcodeLines.value = []
    transferBatches.value = []
    diagnostics.value = []
    currentLayer.value = 0
    currentLayerLineOffset.value = 0
    layerRange.value = [0, 0]
    codeScrollTop.value = 0
    return
  }

  loading.value = true
  errorMessage.value = ''
  diagnostics.value = []
  const totalStartedAt = performance.now()

  try {
    const downloadStartedAt = performance.now()
    const response = await fetch(props.gcodeUrl, {
      headers: { Authorization: `Bearer ${loadAuthToken()}` },
    })
    if (!response.ok) throw new Error(`G-code 加载失败：${response.status}`)

    const gcode = await response.text()
    const downloadDurationMs = performance.now() - downloadStartedAt

    let parsed: RawParsedGcode
    let workerParseDurationMs: number | null = null
    let workerRoundTripDurationMs = 0
    let fallbackParseDurationMs: number | null = null

    try {
      const workerResult = await parseGcodeInWorker(gcode)
      parsed = workerResult.payload
      workerParseDurationMs = workerResult.workerParseDurationMs
      workerRoundTripDurationMs = workerResult.roundTripDurationMs
    } catch {
      const fallbackStartedAt = performance.now()
      parsed = objectParsedToTransfer(parseGcode(gcode))
      fallbackParseDurationMs = performance.now() - fallbackStartedAt
    }

    const assignStartedAt = performance.now()
    layers.value = parsed.layers
    gcodeLines.value = parsed.lines
    transferBatches.value = parsed.batches
    currentLayer.value = 0
    currentLayerLineOffset.value = 0
    layerRange.value = [0, 0]
    codeScrollTop.value = 0
    const assignDurationMs = performance.now() - assignStartedAt

    const sceneStartedAt = performance.now()
    initScene()
    const sceneDurationMs = performance.now() - sceneStartedAt

    const initialRenderStartedAt = performance.now()
    renderLayers()
    const initialRenderDurationMs = performance.now() - initialRenderStartedAt
    scrollCodeToCurrentLine()

    diagnostics.value = [
      { label: '下载', durationMs: downloadDurationMs },
      ...(workerParseDurationMs === null
        ? []
        : [{ label: 'Worker解析', durationMs: workerParseDurationMs }]),
      ...(workerRoundTripDurationMs
        ? [{ label: 'Worker往返', durationMs: workerRoundTripDurationMs }]
        : []),
      ...(fallbackParseDurationMs === null
        ? []
        : [{ label: '主线程兜底解析', durationMs: fallbackParseDurationMs }]),
      { label: '赋值', durationMs: assignDurationMs },
      { label: '建Buffer', durationMs: lastBufferBuildDurationMs },
      { label: '初始化场景', durationMs: sceneDurationMs },
      { label: '首帧路径', durationMs: initialRenderDurationMs },
      { label: '总计', durationMs: performance.now() - totalStartedAt },
    ]
    console.table(
      diagnostics.value.map((item) => ({
        stage: item.label,
        ms: Math.round(item.durationMs),
      })),
    )
  } catch (error) {
    disposeScene()
    layers.value = []
    gcodeLines.value = []
    transferBatches.value = []
    diagnostics.value = []
    currentLayer.value = 0
    currentLayerLineOffset.value = 0
    layerRange.value = [0, 0]
    codeScrollTop.value = 0
    errorMessage.value = error instanceof Error ? error.message : 'G-code 预览失败'
  } finally {
    loading.value = false
  }
}

watch(() => props.gcodeUrl, loadGcode, { immediate: true })
watch(currentLayer, () => {
  currentLayerLineOffset.value = 0
  renderLayers()
  scrollCodeToCurrentLine()
})
watch(currentLayerLineOffset, () => {
  renderLayers()
  scrollCodeToCurrentLine()
})
watch(
  layerRange,
  (value) => {
    const [lower, upper] = selectedLayerRange.value
    if (value[0] !== lower || value[1] !== upper) {
      layerRange.value = [lower, upper]
      return
    }
    if (currentLayer.value !== upper) {
      currentLayer.value = upper
      return
    }
    renderLayers()
    scrollCodeToCurrentLine()
  },
  { deep: true },
)
watch(
  visibleTypes,
  () => {
    renderLayers()
  },
  { deep: true },
)
onBeforeUnmount(disposeScene)
</script>
