<template>
  <div ref="containerRef" class="model-preview">
    <NSpin v-if="loading" />
    <NEmpty v-else-if="!sourceUrl" description="上传 STL/OBJ 后显示模型" />
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

import { loadAuthToken } from '@/api/client'

const props = withDefaults(
  defineProps<{
    sourceUrl?: string
    filename?: string
    bedSize?: number
  }>(),
  {
    sourceUrl: undefined,
    filename: undefined,
    bedSize: 250,
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
}

function createBed(size: number) {
  const group = new THREE.Group()

  const bed = new THREE.Mesh(
    new THREE.PlaneGeometry(size, size),
    new THREE.MeshStandardMaterial({
      color: '#edf2f7',
      metalness: 0,
      roughness: 0.8,
      side: THREE.DoubleSide,
    }),
  )
  bed.position.z = -0.02
  group.add(bed)

  const grid = new THREE.GridHelper(size, 20, '#7c8da1', '#d7dfe9')
  grid.rotation.x = Math.PI / 2
  group.add(grid)

  const border = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.PlaneGeometry(size, size)),
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

function buildScene(object: THREE.Object3D) {
  const container = containerRef.value
  if (!container) return

  disposeScene()
  fitObjectToBed(object)

  scene = new THREE.Scene()
  scene.background = new THREE.Color('#f8fafc')
  camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 2000)
  camera.up.set(0, 0, 1)
  camera.position.set(props.bedSize * 0.65, -props.bedSize * 0.9, props.bedSize * 0.55)
  camera.lookAt(0, 0, props.bedSize * 0.12)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setSize(container.clientWidth, container.clientHeight)
  container.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0, 0, props.bedSize * 0.12)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.screenSpacePanning = false
  controls.maxDistance = props.bedSize * 3
  controls.update()

  scene.add(createBed(props.bedSize))
  scene.add(new THREE.AmbientLight('#ffffff', 1.9))
  const light = new THREE.DirectionalLight('#ffffff', 2.4)
  light.position.set(80, -120, 180)
  scene.add(light)
  scene.add(object)

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
  if (!props.sourceUrl || !props.filename) {
    disposeScene()
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await fetch(props.sourceUrl, {
      headers: { Authorization: `Bearer ${loadAuthToken()}` },
    })
    if (!response.ok) {
      throw new Error(`模型文件加载失败：${response.status}`)
    }

    const suffix = props.filename.split('.').pop()?.toLowerCase()
    if (suffix === 'stl') {
      const geometry = new STLLoader().parse(await response.arrayBuffer())
      geometry.computeVertexNormals()
      const material = new THREE.MeshStandardMaterial({
        color: '#167782',
        metalness: 0.12,
        roughness: 0.52,
      })
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

watch(() => [props.sourceUrl, props.filename], loadModel, { immediate: true })
onBeforeUnmount(disposeScene)
</script>
