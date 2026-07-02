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
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'

import { loadAuthToken } from '@/api/client'

const props = defineProps<{
  sourceUrl?: string
  filename?: string
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const errorMessage = ref('')

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let animationFrame = 0

function disposeScene() {
  cancelAnimationFrame(animationFrame)
  if (renderer && containerRef.value?.contains(renderer.domElement)) {
    containerRef.value.removeChild(renderer.domElement)
  }
  renderer?.dispose()
  renderer = null
  scene = null
  camera = null
}

function buildScene(object: THREE.Object3D) {
  const container = containerRef.value
  if (!container) return

  disposeScene()

  scene = new THREE.Scene()
  scene.background = new THREE.Color('#f8fafc')
  camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000)
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(container.clientWidth, container.clientHeight)
  container.appendChild(renderer.domElement)

  const box = new THREE.Box3().setFromObject(object)
  const center = box.getCenter(new THREE.Vector3())
  const size = box.getSize(new THREE.Vector3()).length() || 1
  object.position.sub(center)

  camera.position.set(size * 0.8, size * 0.7, size * 1.25)
  camera.lookAt(0, 0, 0)

  scene.add(new THREE.AmbientLight('#ffffff', 2.2))
  const light = new THREE.DirectionalLight('#ffffff', 2)
  light.position.set(4, 6, 8)
  scene.add(light)
  scene.add(object)

  const grid = new THREE.GridHelper(size * 1.4, 12, '#94a3b8', '#d5dde8')
  grid.position.y = -size * 0.35
  scene.add(grid)

  function animate() {
    if (!scene || !camera || !renderer) return
    object.rotation.y += 0.006
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
      const material = new THREE.MeshStandardMaterial({ color: '#167782', metalness: 0.15, roughness: 0.55 })
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
