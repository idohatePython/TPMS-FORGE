import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import { getSegmentDrawRange } from '@/gcode/lineRange'
import { parseGcode } from './gcodeParser.worker'

const phoneHolderGcode = resolve(
  process.cwd(),
  '../../TPMS-FORGE-data/users/user-001/projects/p-1001/outputs/plate_1.gcode',
)
const describePhoneHolder = existsSync(phoneHolderGcode) ? describe : describe.skip

describePhoneHolder('Phone Holder OrcaSlicer preview data', () => {
  it('keeps every bottom-surface extrusion from lines 83 through 138 in the visible range', () => {
    const parsed = parseGcode(readFileSync(phoneHolderGcode, 'utf8'))
    const firstLayer = parsed.layers[0]
    const bottomSurface = parsed.batches.find((batch) => batch.type === 'bottomSurface')

    expect(firstLayer).toMatchObject({ startLine: 48, endLine: 498, z: 0.2, height: 0.2 })
    expect(bottomSurface).toBeDefined()

    const expectedLineNumbers = Array.from({ length: 56 }, (_, index) => index + 83)
    const parsedLineNumbers = Array.from(bottomSurface!.lineNumbers).filter(
      (lineNumber) => lineNumber >= 83 && lineNumber <= 138,
    )
    expect(parsedLineNumbers).toEqual(expectedLineNumbers)

    const drawRange = getSegmentDrawRange(bottomSurface!.lineNumbers, firstLayer.startLine, 461)
    const visibleLineNumbers = Array.from(bottomSurface!.lineNumbers.slice(
      drawRange.startVertex / 2,
      drawRange.startVertex / 2 + drawRange.vertexCount / 2,
    ))
    expect(visibleLineNumbers).toEqual(expect.arrayContaining(expectedLineNumbers))
  })
})
