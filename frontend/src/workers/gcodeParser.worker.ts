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

interface Point {
  x: number
  y: number
  z: number
}

interface RawSegment {
  start: Point
  end: Point
  z: number
  lineNumber: number
  raw: string
  type: SegmentType
  length: number
}

interface RawLayer {
  index: number
  startLine: number
  endLine: number
  z: number | null
  height: number | null
  segments: RawSegment[]
}

interface TransferBatch {
  type: SegmentType
  positions: Float32Array
  lineNumbers: Uint32Array
  zValues: Float32Array
  lengths: Float32Array
}

interface ParserState {
  position: { x: number; y: number; z: number; e: number }
  currentType: SegmentType
  relativeExtrusion: boolean
  relativePositioning: boolean
}

const GCODE_NUMBER = '[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?'

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

function distance(start: Point, end: Point) {
  return Math.hypot(end.x - start.x, end.y - start.y, end.z - start.z)
}

function addSegment(
  targetSegments: RawSegment[],
  currentLayerData: RawLayer | null,
  start: Point,
  end: Point,
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
  targetSegments: RawSegment[],
  currentLayerData: RawLayer | null,
  start: Point,
  end: Point,
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

function createLayer(lineNumber: number, parsedLayers: RawLayer[]) {
  const layer: RawLayer = {
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
  parsedSegments: RawSegment[],
  currentLayerData: RawLayer | null,
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

export function parseGcode(gcode: string) {
  const rawLines = gcode.split(/\r?\n/)
  const parsedLayers: RawLayer[] = []
  const parsedSegments: RawSegment[] = []
  const state: ParserState = {
    position: { x: 0, y: 0, z: 0, e: 0 },
    currentType: 'other',
    relativeExtrusion: false,
    relativePositioning: false,
  }
  let currentLayerData: RawLayer | null = null

  rawLines.forEach((rawLine, index) => {
    const lineNumber = index + 1
    const trimmedRaw = rawLine.trim()

    if (/^;LAYER_CHANGE\b/i.test(trimmedRaw) || /^;LAYER:\s*\d+/i.test(trimmedRaw)) {
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

  const grouped = new Map<SegmentType, RawSegment[]>()
  for (const segment of parsedSegments) {
    const segments = grouped.get(segment.type)
    if (segments) segments.push(segment)
    else grouped.set(segment.type, [segment])
  }

  const batches = [...grouped.entries()].map(([type, segments]) => {
    const positions = new Float32Array(segments.length * 6)
    const lineNumbers = new Uint32Array(segments.length)
    const zValues = new Float32Array(segments.length)
    const lengths = new Float32Array(segments.length)

    segments.forEach((segment, index) => {
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
    lines: rawLines,
    layers: parsedLayers.map(({ index, startLine, endLine, z, height }) => ({
      index,
      startLine,
      endLine,
      z,
      height,
    })),
    batches,
  }
}

const workerScope = typeof self === 'undefined' ? null : (self as unknown as {
  onmessage: ((event: MessageEvent<{ gcode: string }>) => void) | null
  postMessage: (message: unknown, transfer?: Transferable[]) => void
})

if (workerScope) workerScope.onmessage = (event: MessageEvent<{ gcode: string }>) => {
  try {
    const startedAt = performance.now()
    const payload = parseGcode(event.data.gcode)
    const parseDurationMs = performance.now() - startedAt
    const transferables: Transferable[] = payload.batches.flatMap((batch: TransferBatch) => [
      batch.positions.buffer,
      batch.lineNumbers.buffer,
      batch.zValues.buffer,
      batch.lengths.buffer,
    ])
    workerScope.postMessage({ ok: true, payload, parseDurationMs }, transferables)
  } catch (error) {
    workerScope.postMessage({
      ok: false,
      error: error instanceof Error ? error.message : 'G-code 解析失败',
    })
  }
}
