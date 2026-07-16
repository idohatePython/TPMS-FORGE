export interface SegmentDrawRange {
  startVertex: number
  vertexCount: number
}

export function lowerBound(lineNumbers: Uint32Array, lineNumber: number) {
  let left = 0
  let right = lineNumbers.length

  while (left < right) {
    const middle = Math.floor((left + right) / 2)
    if (lineNumbers[middle] < lineNumber) left = middle + 1
    else right = middle
  }

  return left
}

export function countSegmentsUpTo(lineNumbers: Uint32Array, lineNumber: number) {
  let left = 0
  let right = lineNumbers.length

  while (left < right) {
    const middle = Math.floor((left + right) / 2)
    if (lineNumbers[middle] <= lineNumber) left = middle + 1
    else right = middle
  }

  return left
}

export function getSegmentDrawRange(
  lineNumbers: Uint32Array,
  startLine: number,
  endLine: number,
): SegmentDrawRange {
  const startSegment = lowerBound(lineNumbers, startLine)
  const endSegment = countSegmentsUpTo(lineNumbers, endLine)
  return {
    startVertex: startSegment * 2,
    vertexCount: Math.max(endSegment - startSegment, 0) * 2,
  }
}
