import { keccak_256 } from '@noble/hashes/sha3.js'
import { toHex } from '../internal/bytes.js'

/** Generic multi-frame QR transport: splits an oversized string payload into
 *  scannable QR frames and reassembles them on the other end. Deliberately
 *  payload-agnostic (plain string in, plain string out) — it knows nothing
 *  about action proposals or pairing payloads specifically, which is what
 *  lets a reassembled payload flow back through whatever generic classifier
 *  the caller already uses (`classifyScannedCode`) instead of a
 *  codec-specific one.
 *
 *  This package never renders a QR image itself, here as everywhere else: it
 *  returns the strings to encode and consumes the strings a scanner read. */

export const QR_FRAME_CODEC = 'OBQR2'
/** `OBQR2|<kind>|<8 hex>|<2-digit index>|<2-digit total>|` — constant width,
 *  so the body can always be recovered with a fixed `slice`, never a
 *  `split('|')` (the body is itself often JSON and freely contains `|`). */
export const QR_FRAME_HEADER_LENGTH = 23
/** v11 @ ECL M (a typical QR library default) holds 251 bytes; 11 bytes of
 *  slack against a different segmentation choice or a future header field.
 *  61 modules at a ~220pt display box stays comfortably scannable. */
export const QR_FRAME_MAX_BYTES = 240
export const QR_FRAME_BODY_MAX_BYTES = QR_FRAME_MAX_BYTES - QR_FRAME_HEADER_LENGTH
/** At or below this, `encodeQrFrames` returns the payload UNFRAMED — no
 *  prefix, byte-identical to what a caller would have rendered directly.
 *  Keeps every single-frame payload on the exact same path it uses without
 *  this module at all. */
export const QR_SINGLE_FRAME_MAX_BYTES = 300
/** ~21.4 KB ceiling (99 * 217 body bytes). */
export const QR_MAX_FRAMES = 99
/** Recommended display cadence for a producer cycling frames: ~4 fps, well
 *  above the ~65-130ms a phone camera needs to lock a code, and below the
 *  500ms identical-event throttle scanner libraries commonly apply (which
 *  only ever compares against the immediately previous event, so distinct
 *  cycling frames are never throttled). */
export const QR_FRAME_INTERVAL_MS = 250

/** How long a partially-collected transfer survives without a new frame
 *  before the accumulator drops it, so a walked-away-from transfer cannot
 *  poison the next one. Exported, not just defaulted, because a consumer
 *  typically needs the same window a second time for its own UI timer (the
 *  accumulator only re-checks staleness on the next `accept()` call, so
 *  nothing clears a progress indicator that has simply stopped moving) —
 *  and a consumer that hardcodes its own copy silently keeps the old window
 *  the day this one is retuned. */
export const QR_FRAME_STALE_MS = 8000

/** A frame's kind tag is ADVISORY and opaque to this module: nothing here
 *  parses the body or checks that it matches the tag. It exists so a scanner
 *  that accepts framed transfers of one kind can drop another kind's
 *  transfer at its FIRST frame, instead of collecting every frame and only
 *  discovering the mismatch after reassembly. A scanner that accepts
 *  everything, or that refuses frames outright, can ignore it entirely. */
export const QR_FRAME_KIND_UNSPECIFIED = '-'
export const QR_FRAME_KIND_ACTION_PROPOSAL = 'p'
export const QR_FRAME_KIND_READ_ONLY_PAIRING = 'r'

/** One character, so the header stays fixed-width. */
const KIND_RE = /^[A-Za-z-]$/

export class QrPayloadTooLargeError extends Error {
  readonly requiredFrames: number
  readonly maxFrames: number
  constructor(requiredFrames: number, maxFrames: number) {
    super(`Payload requires ${requiredFrames} QR frames, exceeding the ${maxFrames}-frame limit`)
    this.name = 'QrPayloadTooLargeError'
    this.requiredFrames = requiredFrames
    this.maxFrames = maxFrames
  }
}

export type QrFrame = { kind: string; transferId: string; index: number; total: number; body: string }
export type QrFrameProgress = { kind: string; transferId: string; received: number; total: number }

export type QrFrameAcceptResult =
  /** Not a frame of this codec, or a frame whose kind `acceptKind` refused —
   *  state untouched, caller should classify it (or drop it) as it would any
   *  other unrecognized scan. */
  | { status: 'ignored' }
  /** Prefix matched but the frame was malformed — state untouched, caller
   *  should drop it silently and stay armed. */
  | { status: 'discarded' }
  /** Accepted (new frame, or a duplicate of one already held). */
  | { status: 'progress'; progress: QrFrameProgress }
  /** A different transfer (new transferId/kind/total, or the prior collection
   *  went stale) interrupted an in-progress one — prior buffer dropped,
   *  collection restarted from this frame. */
  | { status: 'restarted'; progress: QrFrameProgress }
  /** All frames in and the payload hashes back to the transfer id. Emitted
   *  exactly once: internal state resets before returning. */
  | { status: 'complete'; payload: string }
  /** All frames in but the hash check failed — state reset, start over. */
  | { status: 'corrupt' }

export type QrFrameAccumulator = {
  accept(data: string): QrFrameAcceptResult
  progress(): QrFrameProgress | null
  reset(): void
}

const FRAME_PREFIX_RE = /^OBQR2\|([A-Za-z-])\|([0-9a-f]{8})\|(\d{2})\|(\d{2})\|/

/** First 4 bytes of keccak256(payload) — deterministic (no RNG to stub in
 *  tests), and doubles as a free integrity check on reassembly. */
function transferIdFor(payload: string): string {
  return toHex(keccak_256(new TextEncoder().encode(payload)).slice(0, 4))
}

/** UTF-8 byte length of one code point. A lone surrogate (never produced by
 *  well-formed `JSON.stringify` output, but handled defensively) is mapped to
 *  3 bytes — the correct WTF-8 length, not just a safety margin. */
function utf8ByteLengthOfCodePoint(ch: string): number {
  const cp = ch.codePointAt(0) ?? 0
  if (cp <= 0x7f) return 1
  if (cp <= 0x7ff) return 2
  if (cp <= 0xffff) return 3
  return 4
}

function utf8ByteLength(payload: string): number {
  let n = 0
  for (const ch of payload) n += utf8ByteLengthOfCodePoint(ch)
  return n
}

/** Split by a UTF-8 BYTE budget, iterating with `for...of` — which yields
 *  whole code points, so a cut can never land inside a surrogate pair. Byte
 *  (not character) budgeting matters too: QR byte-mode capacity is bytes, so
 *  a character budget would pass every ASCII test and silently overflow on a
 *  French- or CJK-language payload. Only used to find the MINIMUM frame
 *  count (a tight greedy pack); the actual split for that count is
 *  `splitIntoFrameCount` below, which balances sizes instead of dumping
 *  everything short into a near-empty last frame. */
function splitByUtf8Budget(payload: string, budgetBytes: number): string[] {
  const out: string[] = []
  let cur = ''
  let curBytes = 0
  for (const ch of payload) {
    const n = utf8ByteLengthOfCodePoint(ch)
    if (curBytes + n > budgetBytes) {
      out.push(cur)
      cur = ''
      curBytes = 0
    }
    cur += ch
    curBytes += n
  }
  if (cur) out.push(cur)
  return out
}

/** Split into exactly `frameCount` frames, each carrying as near an equal
 *  byte share as code-point boundaries allow. Keeps every frame at the same
 *  QR version/density: a code that visibly gets sparser on its last frame
 *  sends a scanner's autofocus hunting.
 *
 *  The target is recomputed from the bytes and frames still OUTSTANDING after
 *  each flush, rather than precomputed once per index. That distinction is
 *  load-bearing, not a refactor. A frame can only end on a code-point
 *  boundary, so it undershoots its target by up to one code point's width;
 *  with a fixed target array that shortfall is never reclaimed and every
 *  frame repeats it, so the accumulated slack eventually spills past the last
 *  planned frame and opens another one. On multi-byte payloads that was the
 *  normal outcome, not an edge case: `'日'.repeat(121)` (363 bytes, 2 frames'
 *  worth) came out as three frames of 180/180/3 bytes, i.e. exactly the
 *  near-empty trailing frame this function exists to avoid, and a 20,996-byte
 *  emoji payload was rejected as needing 100 frames when 98 sufficed.
 *  Recomputing lets each frame absorb the previous one's shortfall, so the
 *  split lands in `frameCount` frames and stays balanced. */
function splitIntoFrameCount(payload: string, frameCount: number): string[] {
  let remainingBytes = utf8ByteLength(payload)
  let remainingFrames = frameCount
  const targetFor = () => (remainingFrames > 0
    ? Math.min(Math.ceil(remainingBytes / remainingFrames), QR_FRAME_BODY_MAX_BYTES)
    : QR_FRAME_BODY_MAX_BYTES)

  const out: string[] = []
  let cur = ''
  let curBytes = 0
  let target = targetFor()
  for (const ch of payload) {
    const n = utf8ByteLengthOfCodePoint(ch)
    if (curBytes + n > target) {
      out.push(cur)
      remainingBytes -= curBytes
      remainingFrames -= 1
      target = targetFor()
      cur = ''
      curBytes = 0
    }
    cur += ch
    curBytes += n
  }
  if (cur) out.push(cur)
  return out
}

/** Split an already-encoded string payload into scannable QR frames. Returns
 *  `[payload]` UNCHANGED when it fits `QR_SINGLE_FRAME_MAX_BYTES`, so a short
 *  payload never gains a prefix and `opts.kind` is simply unused. Throws
 *  `QrPayloadTooLargeError` above `QR_MAX_FRAMES`.
 *
 *  `opts.kind` is the advisory tag described on `QR_FRAME_KIND_UNSPECIFIED`;
 *  it must be a single `[A-Za-z-]` character, because the header is
 *  fixed-width. Anything else throws rather than emitting frames that would
 *  not re-parse. */
export function encodeQrFrames(payload: string, opts?: { kind?: string }): string[] {
  const kind = opts?.kind ?? QR_FRAME_KIND_UNSPECIFIED
  if (!KIND_RE.test(kind)) {
    throw new Error(`invalid QR frame kind ${JSON.stringify(kind)}: expected a single [A-Za-z-] character`)
  }
  if (utf8ByteLength(payload) <= QR_SINGLE_FRAME_MAX_BYTES) return [payload]

  const minFrames = splitByUtf8Budget(payload, QR_FRAME_BODY_MAX_BYTES).length
  if (minFrames > QR_MAX_FRAMES) throw new QrPayloadTooLargeError(minFrames, QR_MAX_FRAMES)

  const bodies = splitIntoFrameCount(payload, minFrames)
  // The balancing split can rarely run one or two frames longer than
  // `minFrames` (see splitIntoFrameCount) — re-check the ceiling against the
  // actual result rather than trusting the estimate.
  if (bodies.length > QR_MAX_FRAMES) throw new QrPayloadTooLargeError(bodies.length, QR_MAX_FRAMES)

  const transferId = transferIdFor(payload)
  const total = bodies.length
  return bodies.map((body, index) => (
    `${QR_FRAME_CODEC}|${kind}|${transferId}|${String(index).padStart(2, '0')}|${String(total).padStart(2, '0')}|${body}`
  ))
}

/** Cheap prefix test — no parse, no throw. A string that passes this but
 *  fails `parseQrFrame` is OUR garbage, not an unknown code, so the caller
 *  must drop it silently rather than fall through to generic classification. */
export function isQrFrame(data: string): boolean {
  return data.startsWith(`${QR_FRAME_CODEC}|`)
}

/** Parse one frame. `null` on any malformed header, bad kind, bad hex,
 *  non-numeric index/total, `index >= total`, `total === 0`, or empty body.
 *  The body is returned verbatim — it is recovered by fixed offset, never
 *  `split('|')`, so it may itself contain `|`. */
export function parseQrFrame(data: string): QrFrame | null {
  const m = FRAME_PREFIX_RE.exec(data)
  if (!m) return null
  const [, kind, transferId, indexStr, totalStr] = m
  const index = Number(indexStr)
  const total = Number(totalStr)
  if (total === 0 || index >= total) return null
  const body = data.slice(QR_FRAME_HEADER_LENGTH)
  if (!body) return null
  // The encoder never emits a body over this, so one that exceeds it did not
  // come from `encodeQrFrames`. Rejecting here rather than buffering it keeps
  // the ceiling a property of the FORMAT instead of only of the encoder: an
  // accumulator fed from something other than a camera (a deep link, a paste,
  // an NFC read) would otherwise retain an unbounded body per frame slot.
  if (utf8ByteLength(body) > QR_FRAME_BODY_MAX_BYTES) return null
  return { kind, transferId, index, total, body }
}

type AccumulatorState = {
  kind: string
  transferId: string
  total: number
  buf: (string | undefined)[]
  received: number
  lastAcceptedAt: number
}

/** Stateful reassembly buffer, one per scanner instance (never a module
 *  singleton — several screens may each hold their own scanner). Duplicate
 *  frames are the common case (a ~30fps camera reads the same displayed
 *  frame several times before it cycles), so duplicate detection is an O(1)
 *  `buf[i] !== undefined` check, not an allocation.
 *
 *  `acceptKind`, when given, is consulted on every frame BEFORE any state is
 *  touched: a refused kind returns `{status:'ignored'}` and buffers nothing,
 *  which is what lets a single-purpose scanner sit in front of a producer
 *  cycling some other kind without ever filling its buffer. Defaults to
 *  accepting every kind. */
export function createQrFrameAccumulator(opts?: {
  staleMs?: number
  now?: () => number
  acceptKind?: (kind: string) => boolean
}): QrFrameAccumulator {
  const staleMs = opts?.staleMs ?? QR_FRAME_STALE_MS
  const now = opts?.now ?? Date.now
  const acceptKind = opts?.acceptKind
  let state: AccumulatorState | null = null

  return {
    accept(data: string): QrFrameAcceptResult {
      if (!isQrFrame(data)) return { status: 'ignored' }
      const frame = parseQrFrame(data)
      if (!frame) return { status: 'discarded' }
      if (acceptKind && !acceptKind(frame.kind)) return { status: 'ignored' }

      // Captured before the stale-drop below: a timed-out collection still
      // counts as "there was a prior collection being interrupted" for the
      // 'restarted' vs 'progress' distinction.
      const hadPriorState = state !== null
      if (state && now() - state.lastAcceptedAt > staleMs) state = null

      // `kind` participates in transfer identity even though `transferId` is
      // a hash of the payload alone: the same payload framed under two kinds
      // shares a transferId, and treating those as one transfer would
      // interleave two producers' frames into a single buffer.
      const isSameTransfer = state !== null
        && state.transferId === frame.transferId
        && state.kind === frame.kind
        && state.total === frame.total

      let s: AccumulatorState
      if (isSameTransfer && state) {
        s = state
      } else {
        s = {
          kind: frame.kind,
          transferId: frame.transferId,
          total: frame.total,
          buf: new Array(frame.total).fill(undefined),
          received: 0,
          lastAcceptedAt: now(),
        }
        state = s
      }

      if (s.buf[frame.index] === undefined) {
        s.buf[frame.index] = frame.body
        s.received += 1
      }
      s.lastAcceptedAt = now()

      if (s.received < s.total) {
        const progress: QrFrameProgress = {
          kind: s.kind,
          transferId: s.transferId,
          received: s.received,
          total: s.total,
        }
        return { status: hadPriorState && !isSameTransfer ? 'restarted' : 'progress', progress }
      }

      // Complete — emitted exactly once: state resets before returning,
      // whether the integrity check passes or not.
      const payload = s.buf.join('')
      const intact = transferIdFor(payload) === s.transferId
      state = null
      return intact ? { status: 'complete', payload } : { status: 'corrupt' }
    },

    progress(): QrFrameProgress | null {
      return state
        ? { kind: state.kind, transferId: state.transferId, received: state.received, total: state.total }
        : null
    },

    reset(): void {
      state = null
    },
  }
}
