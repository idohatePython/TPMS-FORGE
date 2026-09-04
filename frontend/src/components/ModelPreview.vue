<template>
  <div ref="containerRef" class="model-preview">
    <NSpin v-if="loading" />
    <NEmpty v-else-if="!sourceUrl && !modelData" :description="emptyDescription" />
    <NAlert v-else-if="errorMessage" type="error" :title="errorMessage" />
  </div>
</template>

<script setup lang="ts">
import { NAlert, NEmpty, NSpin } from 'naive-ui'
import { onBeforeUnmount, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import { mergeVertices } from 'three/examples/jsm/utils/BufferGeometryUtils.js'

import { loadAuthToken } from '@/api/client'

const props = withDefaults(
  defineProps<{
    sourceUrl?: string
    filename?: string
    infillPattern?: string
    infillDensity?: number
    modelData?: ArrayBuffer
    bedSize?: number
    emptyDescription?: string
  }>(),
  {
    sourceUrl: undefined,
    filename: undefined,
    infillPattern: undefined,
    infillDensity: undefined,
    modelData: undefined,
    bedSize: 250,
    emptyDescription: '上传 STL/OBJ 后显示模型',
  },
)

const containerRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const errorMessage = ref('')

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let resizeObserver: ResizeObserver | null = null
let animationFrame = 0

function prepareMeshGeometry(geometry: THREE.BufferGeometry) {
  // STL stores every triangle independently. A slightly relaxed merge joins
  // coincident vertices from neighbouring marching-cubes cells, allowing
  // Three.js to calculate continuous normals instead of a faceted triangle
  // look. The tolerance is still only 0.0005 mm for normal project scales.
  const mergedGeometry = mergeVertices(geometry, 5e-4)
  mergedGeometry.computeVertexNormals()
  mergedGeometry.normalizeNormals()
  mergedGeometry.center()
  return mergedGeometry
}

function createTpmsMaterial(infillPattern?: string) {
  return new THREE.MeshPhysicalMaterial({
    color: infillPattern ? '#c8d8d5' : '#e4e8e8',
    transparent: Boolean(infillPattern),
    // In ordinary mode the shell is only context; the lattice members should
    // remain the visual focus, like nTop's implicit-body preview.
    opacity: infillPattern ? 0.3 : 1,
    metalness: 0.02,
    roughness: 0.42,
    clearcoat: 0.16,
    clearcoatRoughness: 0.68,
    flatShading: false,
    side: THREE.DoubleSide,
  })
}

function disposeObject(object: THREE.Object3D) {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh) {
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
}

function fitObjectToBed(object: THREE.Object3D) {
  const box = new THREE.Box3().setFromObject(object)
  const center = box.getCenter(new THREE.Vector3())
  const min = box.min
  object.position.sub(new THREE.Vector3(center.x, center.y, min.z))
  return new THREE.Box3().setFromObject(object)
}

function createBed(width: number, depth: number) {
  const group = new THREE.Group()

  const bed = new THREE.Mesh(
    new THREE.PlaneGeometry(width, depth),
    new THREE.MeshStandardMaterial({
      color: '#edf2f7',
      metalness: 0,
      roughness: 0.8,
      side: THREE.DoubleSide,
    }),
  )
  bed.position.z = -0.02
  bed.receiveShadow = true
  group.add(bed)

  const gridSize = Math.max(width, depth)
  const grid = new THREE.GridHelper(gridSize, 20, '#7c8da1', '#d7dfe9')
  grid.rotation.x = Math.PI / 2
  grid.scale.set(width / gridSize, 1, depth / gridSize)
  group.add(grid)

  const border = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.PlaneGeometry(width, depth)),
    new THREE.LineBasicMaterial({ color: '#39556d' }),
  )
  group.add(border)

  return group
}

function setRendererSize() {
  const container = containerRef.value
  if (!container || !renderer || !camera) return

  const width = container.clientWidth
  const height = container.clientHeight
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

interface FootprintPoint {
  x: number
  y: number
}

function convexHull(points: FootprintPoint[]) {
  const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y)
  if (sorted.length < 3) return sorted
  const cross = (origin: FootprintPoint, pointA: FootprintPoint, pointB: FootprintPoint) =>
    (pointA.x - origin.x) * (pointB.y - origin.y) - (pointA.y - origin.y) * (pointB.x - origin.x)
  const lower: FootprintPoint[] = []
  sorted.forEach((point) => {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], point) <= 0) lower.pop()
    lower.push(point)
  })
  const upper: FootprintPoint[] = []
  for (let index = sorted.length - 1; index >= 0; index -= 1) {
    const point = sorted[index]
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], point) <= 0) upper.pop()
    upper.push(point)
  }
  return lower.slice(0, -1).concat(upper.slice(0, -1))
}

function pointInPolygon(point: FootprintPoint, polygon: FootprintPoint[]) {
  let inside = false
  for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index++) {
    const current = polygon[index]
    const prior = polygon[previous]
    const intersects = current.y > point.y !== prior.y > point.y
      && point.x < ((prior.x - current.x) * (point.y - current.y)) / (prior.y - current.y || 0.00001) + current.x
    if (intersects) inside = !inside
  }
  return inside
}

function addPreviewSegment(target: number[], start: FootprintPoint, end: FootprintPoint, hull: FootprintPoint[], z: number) {
  addPreview3dSegment(target, { x: start.x, y: start.y, z }, { x: end.x, y: end.y, z }, hull)
}

function addPreview3dSegment(
  target: number[],
  start: { x: number; y: number; z: number },
  end: { x: number; y: number; z: number },
  hull: FootprintPoint[],
) {
  const subdivisions = 16
  for (let step = 0; step < subdivisions; step += 1) {
    const t0 = step / subdivisions
    const t1 = (step + 1) / subdivisions
    const a = {
      x: start.x + (end.x - start.x) * t0,
      y: start.y + (end.y - start.y) * t0,
      z: start.z + (end.z - start.z) * t0,
    }
    const b = {
      x: start.x + (end.x - start.x) * t1,
      y: start.y + (end.y - start.y) * t1,
      z: start.z + (end.z - start.z) * t1,
    }
    const midpoint = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
    if (pointInPolygon(midpoint, hull)) target.push(a.x, a.y, a.z, b.x, b.y, b.z)
  }
}

function createInfillPreview(object: THREE.Object3D, bounds: THREE.Box3, pattern: string, density = 15) {
  object.updateMatrixWorld(true)
  const footprintPoints: FootprintPoint[] = []
  object.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return
    const position = child.geometry.getAttribute('position')
    if (!position) return
    // The preview only needs the footprint. Sampling keeps a large uploaded
    // STL from blocking the UI while the actual slicer still receives the
    // complete mesh.
    const sampleStride = Math.max(1, Math.ceil(position.count / 12000))
    for (let index = 0; index < position.count; index += sampleStride) {
      const point = new THREE.Vector3(position.getX(index), position.getY(index), position.getZ(index))
      child.localToWorld(point)
      footprintPoints.push({ x: point.x, y: point.y })
    }
  })
  const hull = convexHull(footprintPoints)
  if (hull.length < 3) return null

  const size = bounds.getSize(new THREE.Vector3())
  // Keep this preview light enough for the browser while still responding to
  // the same density control used by the slicing request. Higher density means
  // tighter path spacing; the actual printable result remains the G-code.
  const normalizedDensity = THREE.MathUtils.clamp(density, 5, 80)
  const densityScale = Math.sqrt(15 / normalizedDensity)
  const cell = Math.max(Math.min((Math.max(size.x, size.y) / 13) * densityScale, 22), 3)
  const linePositions: number[] = []
  const layerCount = Math.max(2, Math.min(5, Math.round(size.z / Math.max(cell, 1))))
  const zStep = size.z / (layerCount + 1)
  const xStart = bounds.min.x - cell
  const xEnd = bounds.max.x + cell
  const yStart = bounds.min.y - cell
  const yEnd = bounds.max.y + cell

  const layerZs = Array.from({ length: layerCount }, (_, index) => bounds.min.z + zStep * (index + 1))
  for (let layer = 0; layer < layerZs.length; layer += 1) {
    const z = layerZs[layer]
    const addLine = (start: FootprintPoint, end: FootprintPoint) => {
      addPreviewSegment(linePositions, start, end, hull, z)
    }
    if (pattern === 'honeycomb') {
      const radius = cell * 0.46
      for (let y = yStart; y <= yEnd; y += radius * 1.72) {
        for (let x = xStart; x <= xEnd; x += radius * 3) {
          const offset = Math.round((y - yStart) / (radius * 1.72)) % 2 ? radius * 1.5 : 0
          const center = { x: x + offset, y }
          const points = Array.from({ length: 7 }, (_, index) => ({
            x: center.x + radius * Math.cos(Math.PI / 3 * index),
            y: center.y + radius * Math.sin(Math.PI / 3 * index),
          }))
          for (let index = 0; index < 6; index += 1) addLine(points[index], points[index + 1])
        }
      }
    } else {
      for (let y = yStart; y <= yEnd; y += cell) {
        if (pattern === 'gyroid') {
          const samples = 24
          for (let sample = 0; sample < samples; sample += 1) {
            const x0 = xStart + (xEnd - xStart) * sample / samples
            const x1 = xStart + (xEnd - xStart) * (sample + 1) / samples
            addLine({ x: x0, y: y + Math.sin(x0 / cell * 1.8) * cell * 0.32 }, { x: x1, y: y + Math.sin(x1 / cell * 1.8) * cell * 0.32 })
          }
        } else if (pattern === 'triangles' || pattern === 'cubic') {
          addLine({ x: xStart, y }, { x: xEnd, y: y + (pattern === 'cubic' ? cell * 2 : 0) })
        } else {
          addLine({ x: xStart, y }, { x: xEnd, y })
        }
      }
      if (pattern !== 'rectilinear') {
        for (let x = xStart; x <= xEnd; x += cell) {
          if (pattern === 'gyroid') {
            const samples = 24
            for (let sample = 0; sample < samples; sample += 1) {
              const y0 = yStart + (yEnd - yStart) * sample / samples
              const y1 = yStart + (yEnd - yStart) * (sample + 1) / samples
              addLine(
                { x: x + Math.sin(y0 / cell * 1.8 + Math.PI / 2) * cell * 0.32, y: y0 },
                { x: x + Math.sin(y1 / cell * 1.8 + Math.PI / 2) * cell * 0.32, y: y1 },
              )
            }
          } else {
            addLine({ x, y: yStart }, { x, y: yEnd })
          }
        }
      }
      if (pattern === 'triangles' || pattern === 'cubic') {
        for (let offset = xStart - size.y; offset < xEnd + size.y; offset += cell * 2) {
          addLine({ x: offset, y: yStart }, { x: offset + size.y, y: yEnd })
          if (pattern === 'cubic') addLine({ x: offset, y: yEnd }, { x: offset + size.y, y: yStart })
        }
      }
    }

    // Add the out-of-plane members that turn the preview into a volume
    // lattice. These are intentionally sparse: the browser preview should
    // communicate the 3D unit-cell structure without competing with the
    // final G-code toolpath or freezing on a dense STL.
    if (layer < layerZs.length - 1) {
      const nextZ = layerZs[layer + 1]
      for (let x = xStart; x <= xEnd; x += cell) {
        for (let y = yStart; y <= yEnd; y += cell) {
          const node = { x, y }
          if (pattern === 'gyroid') {
            node.x += Math.sin(y / cell * 1.8 + Math.PI / 2) * cell * 0.32
            node.y += Math.sin(x / cell * 1.8) * cell * 0.32
          }
          addPreview3dSegment(linePositions, { x: node.x, y: node.y, z }, { x: node.x, y: node.y, z: nextZ }, hull)

          if (pattern === 'cubic' || pattern === 'triangles') {
            const diagonalX = x + cell
            const diagonalY = y + cell
            addPreview3dSegment(linePositions, { x, y, z }, { x: diagonalX, y: diagonalY, z: nextZ }, hull)
            if (pattern === 'cubic') {
              addPreview3dSegment(linePositions, { x: diagonalX, y, z }, { x, y: diagonalY, z: nextZ }, hull)
            }
          }
        }
      }
    }
  }
  if (!linePositions.length) return null
  const positions = new Float32Array(linePositions)
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  const material = new THREE.LineBasicMaterial({
    color: '#0f766e',
    transparent: true,
    opacity: 0.9,
    depthTest: false,
    depthWrite: false,
  })
  const lines = new THREE.LineSegments(geometry, material)
  lines.renderOrder = 4
  return lines
}

function buildScene(object: THREE.Object3D) {
  const container = containerRef.value
  if (!container) return

  disposeScene()
  const fittedBox = fitObjectToBed(object)
  const modelCenter = fittedBox.getCenter(new THREE.Vector3())
  const modelSize = fittedBox.getSize(new THREE.Vector3())
  const modelMaxSize = Math.max(modelSize.x, modelSize.y, modelSize.z, 1)
  const viewTarget = new THREE.Vector3(0, 0, modelCenter.z + modelSize.z * 0.08)
  const aspect = Math.max(container.clientWidth / container.clientHeight, 0.1)
  const verticalFov = THREE.MathUtils.degToRad(45)
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * aspect)
  const limitingFov = Math.min(verticalFov, horizontalFov)
  const boundingRadius = Math.max(modelSize.length() / 2, 1)
  const cameraDistance = (boundingRadius / Math.sin(limitingFov / 2)) * 1.2
  const effectiveBedWidth = Math.max(props.bedSize, modelSize.x * 1.15)
  const effectiveBedDepth = Math.max(props.bedSize, modelSize.y * 1.15)
  const effectiveBedSize = Math.max(effectiveBedWidth, effectiveBedDepth)
  const cameraDirection = new THREE.Vector3(0.72, -1, 0.62).normalize()
  object.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      if (props.infillPattern) {
        child.material = createTpmsMaterial(props.infillPattern)
      }
      child.castShadow = true
      child.receiveShadow = true
    }
  })

  scene = new THREE.Scene()
  scene.background = new THREE.Color('#f3f5f5')
  camera = new THREE.PerspectiveCamera(
    45,
    aspect,
    Math.max(cameraDistance / 1000, 0.01),
    Math.max(cameraDistance * 10, modelMaxSize * 10),
  )
  camera.up.set(0, 0, 1)
  camera.position.copy(viewTarget).add(cameraDirection.multiplyScalar(cameraDistance))
  camera.lookAt(viewTarget)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setSize(container.clientWidth, container.clientHeight)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.05
  container.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.copy(viewTarget)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.screenSpacePanning = false
  controls.minDistance = Math.max(modelMaxSize * 0.05, 0.1)
  controls.maxDistance = Math.max(cameraDistance * 4, effectiveBedSize * 3)
  controls.update()

  scene.add(createBed(effectiveBedWidth, effectiveBedDepth))
  scene.add(new THREE.HemisphereLight('#ffffff', '#b7c0c5', 1.7))
  const light = new THREE.DirectionalLight('#ffffff', 2.8)
  light.position.set(80, -120, 180)
  light.castShadow = true
  light.shadow.mapSize.set(2048, 2048)
  scene.add(light)
  const fillLight = new THREE.DirectionalLight('#d8f7f2', 0.8)
  fillLight.position.set(-120, 80, 90)
  scene.add(fillLight)
  scene.add(object)
  if (props.infillPattern) {
    const infillPreview = createInfillPreview(object, fittedBox, props.infillPattern, props.infillDensity)
    if (infillPreview) scene.add(infillPreview)
  }

  resizeObserver = new ResizeObserver(setRendererSize)
  resizeObserver.observe(container)

  function animate() {
    if (!scene || !camera || !renderer) return
    controls?.update()
    renderer.render(scene, camera)
    animationFrame = requestAnimationFrame(animate)
  }

  animate()
}

async function loadModel() {
  if (!props.modelData && (!props.sourceUrl || !props.filename)) {
    disposeScene()
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    if (props.modelData) {
      const geometry = prepareMeshGeometry(new STLLoader().parse(props.modelData))
      const material = createTpmsMaterial(props.infillPattern)
      buildScene(new THREE.Mesh(geometry, material))
      return
    }

    const sourceUrl = props.sourceUrl
    const filename = props.filename
    if (!sourceUrl || !filename) return

    const response = await fetch(sourceUrl, {
      headers: { Authorization: `Bearer ${loadAuthToken()}` },
    })
    if (!response.ok) {
      throw new Error(`模型文件加载失败：${response.status}`)
    }

    const contentType = response.headers.get('content-type') ?? ''
    if (contentType.includes('text/html') || contentType.includes('application/json')) {
      throw new Error('模型文件加载失败：服务器返回的不是 STL/OBJ 文件')
    }

    const suffix = filename.split('.').pop()?.toLowerCase()
    if (suffix === 'stl') {
      const geometry = prepareMeshGeometry(new STLLoader().parse(await response.arrayBuffer()))
      const material = createTpmsMaterial(props.infillPattern)
      buildScene(new THREE.Mesh(geometry, material))
    } else if (suffix === 'obj') {
      const text = await response.text()
      const object = new OBJLoader().parse(text)
      buildScene(object)
    } else {
      throw new Error('当前仅支持 STL/OBJ 预览')
    }
  } catch (error) {
    disposeScene()
    errorMessage.value = error instanceof Error ? error.message : '模型预览失败'
  } finally {
    loading.value = false
  }
}

watch(() => [props.sourceUrl, props.filename, props.modelData, props.infillPattern, props.infillDensity], loadModel, { immediate: true })
onBeforeUnmount(disposeScene)
</script>
