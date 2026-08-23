import { describe, it, expect } from 'vitest'
import { keccak_256 } from '@noble/hashes/sha3.js'
import {
  encodeQrFrames, isQrFrame, parseQrFrame, createQrFrameAccumulator,
  QrPayloadTooLargeError, QR_FRAME_MAX_BYTES, QR_FRAME_BODY_MAX_BYTES,
  QR_SINGLE_FRAME_MAX_BYTES, QR_MAX_FRAMES, QR_FRAME_HEADER_LENGTH,
  QR_FRAME_KIND_UNSPECIFIED, QR_FRAME_KIND_ACTION_PROPOSAL, QR_FRAME_KIND_READ_ONLY_PAIRING,
  QR_FRAME_STALE_MS,
} from '../src/protocol/qrFrames.js'

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

function utf8Bytes(s: string): number {
  return Buffer.byteLength(s, 'utf8')
}

const LONE_SURROGATE_RE = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/

function reassemble(frames: string[]): string {
  const acc = createQrFrameAccumulator()
  let result: string | null = null
  for (const f of frames) {
    const r = acc.accept(f)
    if (r.status === 'complete') result = r.payload
  }
  if (result === null) throw new Error('did not complete')
  return result
}

describe('encodeQrFrames', () => {
  it('returns the payload unchanged, unframed, when it fits a single frame', () => {
    const payload = 'x'.repeat(QR_SINGLE_FRAME_MAX_BYTES)
    const frames = encodeQrFrames(payload)
    expect(frames).toEqual([payload])
    expect(isQrFrame(frames[0])).toBe(false)
  })

  it('frames a payload one byte over the single-frame threshold', () => {
    const payload = 'x'.repeat(QR_SINGLE_FRAME_MAX_BYTES + 1)
    const frames = encodeQrFrames(payload)
    expect(frames.length).toBeGreaterThanOrEqual(2)
    for (const f of frames) expect(isQrFrame(f)).toBe(true)
  })

  it('keeps every frame within the byte budget for ASCII, accented, CJK, and emoji payloads', () => {
    const samples = [
      'a'.repeat(3000),
      'é'.repeat(1500), // 2 bytes/char
      '日本語'.repeat(1000), // 3 bytes/char
      '🎉'.repeat(800), // 4 bytes/char (surrogate pair)
      JSON.stringify({ label: 'Café Strategy 日本語 🎉', actions: Array.from({ length: 50 }, (_, i) => ({ i, name: `step-${i}-日本` })) }),
    ]
    for (const payload of samples) {
      const frames = encodeQrFrames(payload)
      for (const f of frames) expect(utf8Bytes(f)).toBeLessThanOrEqual(QR_FRAME_MAX_BYTES)
      expect(reassemble(frames)).toBe(payload)
    }
  })

  it('every frame shares one transferId; indices are sequential; total matches frame count', () => {
    const payload = 'y'.repeat(5000)
    const frames = encodeQrFrames(payload).map((f) => parseQrFrame(f)!)
    const transferId = frames[0].transferId
    frames.forEach((f, i) => {
      expect(f.transferId).toBe(transferId)
      expect(f.index).toBe(i)
      expect(f.total).toBe(frames.length)
    })
  })

  it('balances frame sizes: last frame is not near-empty relative to the others', () => {
    // Every sample here must be MULTI-BYTE. An ASCII payload undershoots its
    // per-frame target by zero, so it satisfies any balance assertion no
    // matter how the split is implemented — an ASCII-only version of this
    // test passed throughout the period when `'日'.repeat(121)` was being
    // split 180/180/3.
    for (const payload of ['z'.repeat(4000), '日'.repeat(121), 'é'.repeat(323), '🎉'.repeat(500), '日本語'.repeat(400)]) {
      const bodies = encodeQrFrames(payload).map((f) => (isQrFrame(f) ? parseQrFrame(f)!.body : f))
      const sizes = bodies.map((b) => utf8Bytes(b))
      // One code point's width (4 bytes max) is the most a frame can undershoot
      // once each frame absorbs the previous one's shortfall.
      expect(Math.max(...sizes) - Math.min(...sizes)).toBeLessThanOrEqual(4)
    }
  })

  it('uses no more frames than the payload actually needs, for multi-byte payloads', () => {
    // Regression: a fixed per-index target array never reclaimed the
    // per-frame undershoot, so the accumulated slack spilled into extra
    // frames. `'日'.repeat(121)` (363 bytes) came out as 3 frames, not 2.
    for (const payload of ['日'.repeat(121), 'é'.repeat(323), '日'.repeat(200), '🎉'.repeat(500)]) {
      const bytes = utf8Bytes(payload)
      // A frame can hold at most floor(BODY_MAX / width) whole code points.
      const width = utf8Bytes([...payload][0])
      const perFrame = Math.floor(QR_FRAME_BODY_MAX_BYTES / width) * width
      expect(encodeQrFrames(payload).length).toBe(Math.ceil(bytes / perFrame))
    }
  })

  it('accepts a multi-byte payload that fits the frame ceiling instead of rejecting it', () => {
    // Regression: 20,996 bytes is inside the 99-frame ceiling, but the spill
    // above pushed the split to 100 frames and threw QrPayloadTooLargeError
    // with a requiredFrames that was not the actual requirement.
    const payload = '🎉'.repeat(5249)
    expect(utf8Bytes(payload)).toBeLessThan(QR_MAX_FRAMES * QR_FRAME_BODY_MAX_BYTES)
    const frames = encodeQrFrames(payload)
    expect(frames.length).toBeLessThanOrEqual(QR_MAX_FRAMES)
    for (const f of frames) expect(utf8Bytes(f)).toBeLessThanOrEqual(QR_FRAME_MAX_BYTES)
    expect(reassemble(frames)).toBe(payload)
  })

  it('round-trips in order', () => {
    const payload = JSON.stringify({ a: 1, b: 'hello world', c: [1, 2, 3] }).repeat(50)
    const frames = encodeQrFrames(payload)
    expect(reassemble(frames)).toBe(payload)
  })

  it('round-trips shuffled, and shuffled with duplicates interleaved', () => {
    const payload = 'w'.repeat(6000)
    const frames = encodeQrFrames(payload)
    const shuffled = [frames[2], frames[0], frames[1], frames[2], frames[0], ...frames.slice(3)]
    expect(reassemble(shuffled)).toBe(payload)
  })

  it('never splits a surrogate pair across a frame boundary, for a range of label lengths', () => {
    // Sweep a label length so an emoji has a chance to land on every
    // candidate cut point relative to the frame body budget.
    for (let padLen = 200; padLen < 260; padLen++) {
      const payload = JSON.stringify({ label: `${'a'.repeat(padLen)}🎉strategy`, filler: 'b'.repeat(500) })
      const frames = encodeQrFrames(payload)
      for (const f of frames) {
        const body = isQrFrame(f) ? parseQrFrame(f)!.body : f
        expect(LONE_SURROGATE_RE.test(body)).toBe(false)
      }
      expect(reassemble(frames.length > 1 ? frames : [frames[0]])).toBe(payload)
    }
  })

  it('a multi-byte payload sized under a CHARACTER budget but over the BYTE budget still splits into valid frames', () => {
    // QR_FRAME_BODY_MAX_BYTES ASCII chars would fit a char-based budget, but
    // each of these is 3 UTF-8 bytes, so it must split into >= 2 frames.
    const payload = '日'.repeat(QR_FRAME_BODY_MAX_BYTES)
    expect(payload.length).toBeLessThanOrEqual(QR_FRAME_BODY_MAX_BYTES) // char count alone looks like it fits
    const frames = encodeQrFrames(payload)
    expect(frames.length).toBeGreaterThan(1)
    for (const f of frames) expect(utf8Bytes(f)).toBeLessThanOrEqual(QR_FRAME_MAX_BYTES)
    expect(reassemble(frames)).toBe(payload)
  })

  it('throws QrPayloadTooLargeError above the frame-count ceiling', () => {
    const payload = 'q'.repeat((QR_MAX_FRAMES + 5) * QR_FRAME_BODY_MAX_BYTES)
    expect(() => encodeQrFrames(payload)).toThrow(QrPayloadTooLargeError)
    try {
      encodeQrFrames(payload)
    } catch (e) {
      expect(e).toBeInstanceOf(QrPayloadTooLargeError)
      expect((e as InstanceType<typeof QrPayloadTooLargeError>).requiredFrames).toBeGreaterThan(QR_MAX_FRAMES)
      expect((e as InstanceType<typeof QrPayloadTooLargeError>).maxFrames).toBe(QR_MAX_FRAMES)
    }
  })
})

describe('encodeQrFrames: kind tag', () => {
  it('defaults to the unspecified kind when opts is omitted', () => {
    const frames = encodeQrFrames('a'.repeat(2000))
    for (const f of frames) expect(parseQrFrame(f)!.kind).toBe(QR_FRAME_KIND_UNSPECIFIED)
  })

  it('carries an explicit kind identically on every frame, and round-trips the payload', () => {
    const payload = 'a'.repeat(3000)
    const frames = encodeQrFrames(payload, { kind: QR_FRAME_KIND_ACTION_PROPOSAL })
    for (const f of frames) expect(parseQrFrame(f)!.kind).toBe(QR_FRAME_KIND_ACTION_PROPOSAL)
    expect(reassemble(frames)).toBe(payload)
  })

  it('the kind does not alter the framed body: two kinds split the same payload identically', () => {
    const payload = 'a'.repeat(3000)
    const a = encodeQrFrames(payload, { kind: QR_FRAME_KIND_ACTION_PROPOSAL }).map((f) => parseQrFrame(f)!.body)
    const b = encodeQrFrames(payload, { kind: QR_FRAME_KIND_READ_ONLY_PAIRING }).map((f) => parseQrFrame(f)!.body)
    expect(a).toEqual(b)
  })

  it('throws on a kind that would break the fixed-width header', () => {
    expect(() => encodeQrFrames('a'.repeat(2000), { kind: 'pp' })).toThrow(/invalid QR frame kind/)
    expect(() => encodeQrFrames('a'.repeat(2000), { kind: '' })).toThrow(/invalid QR frame kind/)
    expect(() => encodeQrFrames('a'.repeat(2000), { kind: '|' })).toThrow(/invalid QR frame kind/)
    expect(() => encodeQrFrames('a'.repeat(2000), { kind: '1' })).toThrow(/invalid QR frame kind/)
  })

  it('validates the kind even for a sub-threshold payload that is returned unframed', () => {
    // The kind is unused on that path, but failing loudly beats letting a
    // caller ship a bad tag that only throws once a payload happens to grow.
    expect(() => encodeQrFrames('short', { kind: 'pp' })).toThrow(/invalid QR frame kind/)
    expect(encodeQrFrames('short', { kind: QR_FRAME_KIND_ACTION_PROPOSAL })).toEqual(['short'])
  })
})

describe('parseQrFrame / isQrFrame', () => {
  it('round-trips a well-formed frame and preserves a body containing "|" verbatim', () => {
    const [frame] = encodeQrFrames('x'.repeat(QR_SINGLE_FRAME_MAX_BYTES + 1))
    const parsed = parseQrFrame(frame)!
    expect(parsed.body.length).toBeGreaterThan(0)

    const withPipe = frame + '|extra|pipes|here'
    const reparsed = parseQrFrame(withPipe)!
    expect(reparsed.body.endsWith('|extra|pipes|here')).toBe(true)
  })

  it('the header is exactly QR_FRAME_HEADER_LENGTH bytes', () => {
    // Asserted against the LITERAL header, not against `frame.length -
    // body.length`: `parseQrFrame` defines the body as `slice(HEADER_LENGTH)`,
    // so that subtraction is identically HEADER_LENGTH for anything that
    // parses at all and cannot detect the regex/constant disagreement this
    // test exists to guard against.
    const [frame] = encodeQrFrames('x'.repeat(2000), { kind: QR_FRAME_KIND_ACTION_PROPOSAL })
    const { transferId, total } = parseQrFrame(frame)!
    const header = `OBQR2|p|${transferId}|00|${String(total).padStart(2, '0')}|`
    expect(header).toHaveLength(QR_FRAME_HEADER_LENGTH)
    expect(frame.startsWith(header)).toBe(true)
  })

  it('rejects a body over the encoder ceiling, so the limit is a property of the format', () => {
    const at = 'A'.repeat(QR_FRAME_BODY_MAX_BYTES)
    expect(parseQrFrame(`OBQR2|-|deadbeef|00|02|${at}`)).not.toBeNull()
    expect(parseQrFrame(`OBQR2|-|deadbeef|00|02|${at}A`)).toBeNull()
    expect(parseQrFrame(`OBQR2|-|deadbeef|00|02|${'A'.repeat(100000)}`)).toBeNull()
    // Multi-byte bodies are measured in BYTES, not code units.
    expect(parseQrFrame(`OBQR2|-|deadbeef|00|02|${'日'.repeat(73)}`)).toBeNull()
  })

  it('rejects malformed frames', () => {
    expect(parseQrFrame('NOTAQR|-|aabbccdd|00|01|body')).toBeNull() // wrong magic
    expect(parseQrFrame('OBQR2|-|AABBCCDD|00|01|body')).toBeNull() // uppercase hex
    expect(parseQrFrame('OBQR2|-|aabbcc|00|01|body')).toBeNull() // short id
    expect(parseQrFrame('OBQR2|-|aabbccdd|0x|01|body')).toBeNull() // non-numeric index
    expect(parseQrFrame('OBQR2|-|aabbccdd|00|0x|body')).toBeNull() // non-numeric total
    expect(parseQrFrame('OBQR2|-|aabbccdd|01|01|body')).toBeNull() // index >= total
    expect(parseQrFrame('OBQR2|-|aabbccdd|00|00|body')).toBeNull() // total === 0
    expect(parseQrFrame('OBQR2|-|aabbccdd|00|01')).toBeNull() // truncated, no body
    expect(parseQrFrame('OBQR2|-|aabbccdd|00|01|')).toBeNull() // empty body
    expect(parseQrFrame('OBQR2|aabbccdd|00|01|body')).toBeNull() // no kind field
    expect(parseQrFrame('OBQR2|pp|aabbccdd|00|01|body')).toBeNull() // two-char kind
    expect(parseQrFrame('OBQR2|1|aabbccdd|00|01|body')).toBeNull() // out-of-alphabet kind
  })

  it('isQrFrame is true for prefix-matching garbage, so the caller drops it rather than misclassifying it', () => {
    expect(isQrFrame('OBQR2|garbage')).toBe(true)
    expect(parseQrFrame('OBQR2|garbage')).toBeNull()
    expect(isQrFrame('{"v":1}')).toBe(false)
  })
})

describe('createQrFrameAccumulator', () => {
  it('duplicate frame: progress unchanged', () => {
    const acc = createQrFrameAccumulator()
    const frames = encodeQrFrames('a'.repeat(2000))
    const r1 = acc.accept(frames[0])
    expect(r1.status).toBe('progress')
    if (r1.status !== 'progress') throw new Error('unreachable')
    expect(r1.progress.received).toBe(1)
    const r2 = acc.accept(frames[0])
    expect(r2.status).toBe('progress')
    if (r2.status !== 'progress') throw new Error('unreachable')
    expect(r2.progress.received).toBe(1)
  })

  it('foreign transferId mid-collection restarts', () => {
    const acc = createQrFrameAccumulator()
    const a = encodeQrFrames('a'.repeat(2000))
    const b = encodeQrFrames('b'.repeat(2000))
    acc.accept(a[0])
    const r = acc.accept(b[0])
    expect(r.status).toBe('restarted')
    if (r.status !== 'restarted') throw new Error('unreachable')
    expect(r.progress.received).toBe(1)
    expect(r.progress.transferId).toBe(parseQrFrame(b[0])!.transferId)
  })

  it('same transferId, different total restarts', () => {
    const acc = createQrFrameAccumulator()
    const frame = parseQrFrame(encodeQrFrames('a'.repeat(2000))[0])!
    acc.accept(`OBQR2|-|${frame.transferId}|00|03|${frame.body}`)
    const r = acc.accept(`OBQR2|-|${frame.transferId}|00|05|${frame.body}`)
    expect(r.status).toBe('restarted')
  })

  it('same payload under a different kind restarts rather than interleaving', () => {
    // transferId hashes the payload alone, so these two transfers share one.
    // Without kind in the identity check their frames would land in a single
    // buffer and reassemble into a mix of two producers' output.
    const acc = createQrFrameAccumulator()
    const payload = 'a'.repeat(2000)
    const p = encodeQrFrames(payload, { kind: QR_FRAME_KIND_ACTION_PROPOSAL })
    const r = encodeQrFrames(payload, { kind: QR_FRAME_KIND_READ_ONLY_PAIRING })
    expect(parseQrFrame(p[0])!.transferId).toBe(parseQrFrame(r[0])!.transferId)
    acc.accept(p[0])
    const restarted = acc.accept(r[1])
    expect(restarted.status).toBe('restarted')
    if (restarted.status !== 'restarted') throw new Error('unreachable')
    expect(restarted.progress.kind).toBe(QR_FRAME_KIND_READ_ONLY_PAIRING)
    expect(restarted.progress.received).toBe(1)
  })

  it('progress reports the transfer kind', () => {
    const acc = createQrFrameAccumulator()
    const frames = encodeQrFrames('a'.repeat(2000), { kind: QR_FRAME_KIND_ACTION_PROPOSAL })
    acc.accept(frames[0])
    expect(acc.progress()?.kind).toBe(QR_FRAME_KIND_ACTION_PROPOSAL)
  })

  it('acceptKind refuses a kind on its FIRST frame and buffers nothing', () => {
    const seen: string[] = []
    const acc = createQrFrameAccumulator({
      acceptKind: (k) => {
        seen.push(k)
        return k === QR_FRAME_KIND_READ_ONLY_PAIRING
      },
    })
    const frames = encodeQrFrames('a'.repeat(2000), { kind: QR_FRAME_KIND_ACTION_PROPOSAL })
    for (const f of frames) expect(acc.accept(f).status).toBe('ignored')
    expect(acc.progress()).toBeNull()
    expect(new Set(seen)).toEqual(new Set([QR_FRAME_KIND_ACTION_PROPOSAL]))
  })

  it('acceptKind does not disturb an in-progress transfer of an accepted kind', () => {
    const acc = createQrFrameAccumulator({ acceptKind: (k) => k === QR_FRAME_KIND_READ_ONLY_PAIRING })
    const payload = 'a'.repeat(2000)
    const wanted = encodeQrFrames(payload, { kind: QR_FRAME_KIND_READ_ONLY_PAIRING })
    const unwanted = encodeQrFrames('b'.repeat(2000), { kind: QR_FRAME_KIND_ACTION_PROPOSAL })
    let result: string | null = null
    for (const f of wanted) {
      expect(acc.accept(unwanted[0]).status).toBe('ignored') // interleaved noise
      const r = acc.accept(f)
      if (r.status === 'complete') result = r.payload
    }
    expect(result).toBe(payload)
  })

  it('acceptKind returning true behaves exactly as no filter', () => {
    const payload = 'a'.repeat(2000)
    const frames = encodeQrFrames(payload, { kind: QR_FRAME_KIND_ACTION_PROPOSAL })
    const acc = createQrFrameAccumulator({ acceptKind: () => true })
    let result: string | null = null
    for (const f of frames) {
      const r = acc.accept(f)
      if (r.status === 'complete') result = r.payload
    }
    expect(result).toBe(payload)
  })

  it('non-frame string is ignored, progress untouched', () => {
    const acc = createQrFrameAccumulator()
    const frames = encodeQrFrames('a'.repeat(2000))
    acc.accept(frames[0])
    const r = acc.accept('some-other-qr-payload')
    expect(r.status).toBe('ignored')
    expect(acc.progress()?.received).toBe(1)
  })

  it('completes exactly once; replaying the final frame after completion starts a new collection', () => {
    const acc = createQrFrameAccumulator()
    const payload = 'a'.repeat(2000)
    const frames = encodeQrFrames(payload)
    let completions = 0
    let lastResult
    for (const f of frames) {
      lastResult = acc.accept(f)
      if (lastResult.status === 'complete') completions++
    }
    expect(completions).toBe(1)
    expect(acc.progress()).toBeNull()

    // Replaying the last frame again starts a FRESH collection (same transferId
    // and total as before, but the buffer was reset on completion) — not a
    // second 'complete'.
    const again = acc.accept(frames[frames.length - 1])
    expect(again.status).toBe('progress')
  })

  it('tampered body fails the integrity check on completion and resets', () => {
    const acc = createQrFrameAccumulator()
    const frames = encodeQrFrames('a'.repeat(2000))
    for (const f of frames.slice(0, -1)) acc.accept(f)
    const last = parseQrFrame(frames[frames.length - 1])!
    const tampered = `OBQR2|${last.kind}|${last.transferId}|${String(last.index).padStart(2, '0')}|${String(last.total).padStart(2, '0')}|${'Z'.repeat(last.body.length)}`
    const r = acc.accept(tampered)
    expect(r.status).toBe('corrupt')
    expect(acc.progress()).toBeNull()
  })

  it('reset() clears progress; reset() on an empty accumulator is a no-op', () => {
    const acc = createQrFrameAccumulator()
    expect(() => acc.reset()).not.toThrow()
    const frames = encodeQrFrames('a'.repeat(2000))
    acc.accept(frames[0])
    expect(acc.progress()).not.toBeNull()
    acc.reset()
    expect(acc.progress()).toBeNull()
  })

  it('defaults its staleness window to QR_FRAME_STALE_MS when no override is given', () => {
    // Every other staleness assertion passes an explicit `staleMs`, so nothing
    // pinned the DEFAULT. Swapping the default for a different constant, or
    // back to a bare literal, would not have failed a single test.
    let t = 0
    const acc = createQrFrameAccumulator({ now: () => t })
    const frames = encodeQrFrames('a'.repeat(2000))
    acc.accept(frames[0])

    t = QR_FRAME_STALE_MS
    expect(acc.accept(frames[1]).status).toBe('progress') // exactly at the window: still fresh

    t = QR_FRAME_STALE_MS * 2 + 1
    const stale = acc.accept(frames[2])
    expect(stale.status).toBe('restarted')
    if (stale.status !== 'restarted') throw new Error('unreachable')
    expect(stale.progress.received).toBe(1)
  })

  it('staleness: a frame after staleMs starts fresh; a frame just before staleMs continues', () => {
    let t = 0
    const acc = createQrFrameAccumulator({ staleMs: 1000, now: () => t })
    const a = encodeQrFrames('a'.repeat(2000))
    acc.accept(a[0])

    t = 999
    const stillFresh = acc.accept(a[1])
    expect(stillFresh.status).toBe('progress')
    if (stillFresh.status !== 'progress') throw new Error('unreachable')
    expect(stillFresh.progress.received).toBe(2)

    t = 999 + 1001
    const stale = acc.accept(a[2])
    expect(stale.status).toBe('restarted')
    if (stale.status !== 'restarted') throw new Error('unreachable')
    expect(stale.progress.received).toBe(1)
  })

  it('total === 1 framed input resolves on the first frame, complete or corrupt', () => {
    // Both outcomes asserted EXACTLY. Accepting either (`toContain`) pinned
    // nothing about the integrity check on this path.
    const body = '{"x":1}'
    const realId = toHex(keccak_256(new TextEncoder().encode(body)).slice(0, 4))

    const good = createQrFrameAccumulator().accept(`OBQR2|-|${realId}|00|01|${body}`)
    expect(good).toEqual({ status: 'complete', payload: body })

    const bad = createQrFrameAccumulator().accept(`OBQR2|-|aabbccdd|00|01|${body}`)
    expect(bad).toEqual({ status: 'corrupt' })
  })
})
