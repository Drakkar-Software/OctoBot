import { generateDeviceKeys, type GeneratedDeviceKeys } from '@drakkar.software/starfish-identities'
import { ed25519Suite } from '@drakkar.software/starfish-protocol'
import { signKemSig } from '@drakkar.software/starfish-spaces'
import { toHex, hexToBytes } from '../internal/bytes.js'
import type { NodeCollectionKey } from '../collections/nodeCollections.js'

/** Excludes visually-ambiguous characters (0/O, 1/I/L) — Crockford-style,
 *  meant to be read off one screen and typed on another. 31 symbols
 *  (23 letters + 8 digits), 8 characters ⇒ 8·log2(31) ≈ 39.63 bits of
 *  entropy, well above RFC 8628's device-flow `user_code` minimum, and
 *  bounded further by the rendezvous collection's short TTL and per-IP
 *  rate limit (not something this package controls). `randomCode()` uses
 *  rejection sampling (see `CODE_REJECT_THRESHOLD`) so this figure is the
 *  real, uniform entropy — not a biased approximation of it. */
const CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
const CODE_LENGTH = 8
// 256 is not a multiple of CODE_ALPHABET.length (31) — a plain `byte %
// length` would over-represent the first `256 % 31 = 8` symbols (A-H) by
// 12.5% in every character position. Reject any byte at or above the
// largest multiple of the alphabet length that still fits in a byte
// (Math.floor(256 / 31) * 31 = 248) and draw a replacement — the remaining
// range [0, 248) maps onto the 31 symbols with exactly uniform probability.
const CODE_REJECT_THRESHOLD = Math.floor(256 / CODE_ALPHABET.length) * CODE_ALPHABET.length
const DEFAULT_REQUEST_TTL_SEC = 5 * 60
// `expiresAt`/`createdAt` are NOT covered by popSig — anyone with the code
// can rewrite them, and the ONLY thing that kept the code's live window
// actually short was the 5-minute default nobody was forced to respect.
// This is the real enforcement: a request whose declared window exceeds it
// is rejected outright by parsePairingRequest, and createPairingRequest
// clamps its own ttlSec to it too so a well-meaning caller can't
// accidentally request something this package would reject anyway.
const MAX_REQUEST_TTL_SEC = 60 * 60

function randomBytes(n: number): Uint8Array {
  const b = new Uint8Array(n)
  globalThis.crypto.getRandomValues(b)
  return b
}

function randomCode(): string {
  const chars: string[] = []
  // Pull a batch at a time (rather than one byte per iteration) so a run of
  // rejected bytes doesn't turn into a syscall-per-byte loop — rejection
  // hits ~3% of bytes, so a fresh CODE_LENGTH-sized batch almost always
  // finishes the code outright, with a further batch only on the rare tail.
  while (chars.length < CODE_LENGTH) {
    const batch = randomBytes(CODE_LENGTH)
    for (const b of batch) {
      if (b >= CODE_REJECT_THRESHOLD) continue
      chars.push(CODE_ALPHABET[b % CODE_ALPHABET.length])
      if (chars.length === CODE_LENGTH) break
    }
  }
  return chars.join('')
}

/** What binds `code`/`devEdPub`/`devKemPub` together and proves the
 *  requester holds `devEdPriv` — without this, a request record's public
 *  keys could be swapped in transit with no way to detect it, and binding
 *  `code` specifically prevents a validly-signed request minted for one
 *  code from being replayed/republished under a DIFFERENT code (the
 *  rendezvous collection is public-write, so anyone who captures a signed
 *  request record could otherwise re-publish it verbatim elsewhere). Signed
 *  over a canonical JSON of the three fields so a signature can't be
 *  replayed across a different (key-pair, code) combination. */
function popSigningInput(code: string, devEdPub: string, devKemPub: string): Uint8Array {
  return new TextEncoder().encode(JSON.stringify({ code, devEdPub, devKemPub }))
}

/** A website's device-code pairing request, published to the `joinsessions`
 *  rendezvous collection (`Infra/sync/server/drakkar_sync/apps/dk_spaces/collections.py`,
 *  `_pairing/session/{code}`) so the phone app can look it up by the short
 *  code the user types in. ONE address serves both phases of the exchange:
 *  this "request" doc is later overwritten in place by the phone's sealed
 *  "grant" doc (see `client/pairing/pairingGrantExchange.ts`) — the two
 *  phases are told apart on the wire by the top-level `kind` field, which
 *  the grant phase carries on an UNSEALED outer envelope specifically so a
 *  poller can tell "not yet approved" from "approved" without needing to
 *  unseal anything. `code` is carried on this payload (not just used as the
 *  address) so `popSig` can bind to it — see `popSigningInput` above — and
 *  so `parsePairingRequest` can reject a request record that doesn't match
 *  the code it was fetched under. */
export interface PairingRequestPayload {
  v: 1
  kind: 'octobot-pairing-request'
  code: string
  /** Who's asking: `'website'` — the original case, a third-party site
   *  running this package in a browser — or `'device'` — another OctoBot
   *  client (e.g. a second phone) pairing as a read-only viewer of this
   *  wallet's cloud mirror. Always present on the wire; there is no
   *  absent-means-website fallback (this package predates any published
   *  consumer, so there was never a shape to stay compatible with). The
   *  approving side (`website-pairing-approve.tsx` in mobile2) branches its
   *  copy on this — a `'device'` request has no real "origin" to verify,
   *  trust instead comes from the human typing the code themselves. */
  requesterKind: 'website' | 'device'
  devEdPub: string
  devKemPub: string
  /** `ed25519Suite.sign(popSigningInput(...), devEdPriv)`, hex. Proves the
   *  requester holds `devEdPriv` — not proof of the requester's identity or
   *  intent, which is exactly why `origin`/`code` are still what the
   *  approving human relies on. */
  popSig: string
  /** `signKemSig({kemPub: devKemPub, edPriv: devEdPriv})` (`@drakkar.software
   *  /starfish-spaces`), hex — a SEPARATE proof-of-possession signature,
   *  over just `devKemPub`, matching the exact `{edPub, kemPub, userId,
   *  kemSig}` "join request" shape `starfish-spaces`' own
   *  `parseJoinRequest`/`inviteToNode` expect. The approving side
   *  reconstructs that join request from `devEdPub`/`devKemPub` (already
   *  present above) plus this field — see `client/pairing/mirrorGrant.ts` —
   *  rather than the website needing to hold a full `starfish-spaces`
   *  `Session` just to call `makeJoinRequest()` for an identity it has no
   *  wallet to derive. */
  joinRequestKemSig: string
  /** Attacker-controlled in the sense that anyone can put any string here —
   *  the approving side must verify it (e.g. a `.well-known` fetch), not
   *  trust it at face value. */
  origin: string
  label?: string
  requestedCollections?: NodeCollectionKey[]
  createdAt: string
  expiresAt: string
  rendezvous: { baseUrl: string; namespace: string }
}

/** Create a pairing request: fresh ephemeral device keys (never the site's
 *  own identity), a proof-of-possession signature, and a short human code.
 *  Returns the code separately from `request` too (in addition to it being
 *  on the payload) since the caller needs it to display immediately, before
 *  `request` is even published. */
export async function createPairingRequest(opts: {
  origin: string
  rendezvous: { baseUrl: string; namespace: string }
  label?: string
  requestedCollections?: NodeCollectionKey[]
  ttlSec?: number
  /** Defaults to `'website'` — the original, still-overwhelmingly-common
   *  caller. Only a device-pairing consumer needs to pass `'device'`
   *  explicitly. The built payload always carries the field either way. */
  requesterKind?: 'website' | 'device'
}): Promise<{ request: PairingRequestPayload; device: GeneratedDeviceKeys; code: string }> {
  const device = generateDeviceKeys()
  const code = randomCode()
  // Clamped, not just defaulted — a caller passing an oversized ttlSec
  // would otherwise create a request parsePairingRequest rejects outright
  // (see MAX_REQUEST_TTL_SEC), silently breaking their own integration
  // instead of getting the shortest safe window this package will accept.
  // Does not clamp a NEGATIVE ttlSec (e.g. for testing an already-expired
  // request) — only the upper bound is enforced here.
  const ttlSec = Math.min(opts.ttlSec ?? DEFAULT_REQUEST_TTL_SEC, MAX_REQUEST_TTL_SEC)
  const now = new Date()
  const popSig = toHex(ed25519Suite.sign(popSigningInput(code, device.edPub, device.kemPub), device.edPriv))
  const joinRequestKemSig = signKemSig({ kemPub: device.kemPub, edPriv: device.edPriv })

  const request: PairingRequestPayload = {
    v: 1,
    kind: 'octobot-pairing-request',
    code,
    requesterKind: opts.requesterKind ?? 'website',
    devEdPub: device.edPub,
    devKemPub: device.kemPub,
    popSig,
    joinRequestKemSig,
    origin: opts.origin,
    ...(opts.label ? { label: opts.label } : {}),
    ...(opts.requestedCollections ? { requestedCollections: opts.requestedCollections } : {}),
    createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + ttlSec * 1000).toISOString(),
    rendezvous: opts.rendezvous,
  }
  return { request, device, code }
}

// Ed25519/X25519 public keys are 32 raw bytes; an Ed25519 signature is 64 —
// hex-encoded, that's exactly these lengths. Checked BEFORE hexToBytes is
// called on any of them: hexToBytes allocates proportionally to input
// length with no ceiling of its own, so an unbounded hex string here would
// allocate before ever reaching signature verification.
const HEX_KEY_LENGTH = 64
const HEX_SIG_LENGTH = 128
const MAX_ORIGIN_LENGTH = 2048
const MAX_LABEL_LENGTH = 200
// C0/C1 control characters (including \n, \r — RN <Text> renders an
// embedded newline as a real line break, letting attacker text masquerade
// as extra app chrome) plus the Unicode bidi override/isolate controls
// (U+202A-E, U+2066-9) that can visually reverse or reorder a rendered
// string — e.g. making a hostile host read as a different one. Written as
// explicit \u escapes, never literal control/bidi characters in source.
const UNSAFE_TEXT_PATTERN = /[\u0000-\u001F\u007F-\u009F\u202A-\u202E\u2066-\u2069]/

function assertBoundedSafeText(value: string, field: string, maxLength: number): void {
  if (value.length > maxLength) throw new Error(`pairing request: ${field} exceeds max length`)
  if (UNSAFE_TEXT_PATTERN.test(value)) {
    throw new Error(`pairing request: ${field} contains a disallowed control or bidi-override character`)
  }
}

function assertHexLength(value: string, field: string, expectedLength: number): void {
  if (value.length !== expectedLength || !/^[0-9a-fA-F]+$/.test(value)) {
    throw new Error(`pairing request: ${field} is not a valid ${expectedLength}-character hex string`)
  }
}

/** Parse and validate a pairing request record fetched by code. `expectedCode`
 *  MUST be the code the caller fetched this record under (from the address,
 *  not the payload) — rejecting a mismatch stops a request record signed
 *  for one code from being accepted after being copied/replayed to a
 *  different code's slot. Verifies the proof-of-possession signature and
 *  rejects an expired request — both before the approving side does
 *  anything else with it. Does NOT verify `origin` resolves to anything
 *  real; that needs an actual network check the approving side performs
 *  itself (this package stays I/O-free here). It DOES bound and
 *  sanity-check `origin`/`label` as strings — a length cap, a URL parse for
 *  `origin`, and rejecting control/bidi-override characters in both — since
 *  they're the two fields an approving human actually reads and relies on.
 *  Full homoglyph/IDNA-confusable host detection is out of scope, the same
 *  judgment call already made for origin verification itself. */
export function parsePairingRequest(payload: string, expectedCode: string): PairingRequestPayload {
  let parsed: unknown
  try {
    parsed = JSON.parse(payload)
  } catch {
    throw new Error('not valid JSON')
  }
  if (typeof parsed !== 'object' || parsed === null) throw new Error('not an object')
  const p = parsed as Record<string, unknown>
  if (p.v !== 1 || p.kind !== 'octobot-pairing-request') throw new Error('not a pairing request payload')
  if (typeof p.code !== 'string' || typeof p.devEdPub !== 'string' || typeof p.devKemPub !== 'string'
    || typeof p.popSig !== 'string' || typeof p.joinRequestKemSig !== 'string' || typeof p.origin !== 'string'
    || typeof p.createdAt !== 'string' || typeof p.expiresAt !== 'string') {
    throw new Error('malformed pairing request payload')
  }
  if (p.requesterKind !== 'website' && p.requesterKind !== 'device') {
    throw new Error('malformed pairing request payload: requesterKind')
  }
  if (p.code !== expectedCode) {
    throw new Error('pairing request: code does not match the address it was fetched from')
  }
  const rendezvous = p.rendezvous as { baseUrl?: unknown; namespace?: unknown } | undefined
  if (!rendezvous || typeof rendezvous.baseUrl !== 'string' || typeof rendezvous.namespace !== 'string') {
    throw new Error('malformed pairing request payload: rendezvous')
  }
  if (p.label !== undefined && typeof p.label !== 'string') {
    throw new Error('malformed pairing request payload: label')
  }

  assertHexLength(p.devEdPub, 'devEdPub', HEX_KEY_LENGTH)
  assertHexLength(p.devKemPub, 'devKemPub', HEX_KEY_LENGTH)
  assertHexLength(p.popSig, 'popSig', HEX_SIG_LENGTH)
  assertHexLength(p.joinRequestKemSig, 'joinRequestKemSig', HEX_SIG_LENGTH)
  assertBoundedSafeText(p.origin, 'origin', MAX_ORIGIN_LENGTH)
  if (p.label !== undefined) assertBoundedSafeText(p.label as string, 'label', MAX_LABEL_LENGTH)
  try {
    new URL(p.origin)
  } catch {
    throw new Error('pairing request: origin is not a valid URL')
  }

  const request = p as unknown as PairingRequestPayload

  const verified = ed25519Suite.verify(
    hexToBytes(request.popSig),
    popSigningInput(request.code, request.devEdPub, request.devKemPub),
    request.devEdPub,
  )
  if (!verified) throw new Error('pairing request: invalid proof-of-possession signature')

  // Date.parse of a malformed string returns NaN, and every comparison
  // against NaN is false — so a garbage expiresAt would otherwise be
  // silently treated as "not expired" instead of rejected. Fail closed.
  const expiresAtMs = Date.parse(request.expiresAt)
  if (!Number.isFinite(expiresAtMs) || expiresAtMs <= Date.now()) throw new Error('pairing request: expired')

  // The actual enforcement of "short-lived code" — expiresAt/createdAt are
  // NOT covered by popSig, so a party with the code can rewrite either to
  // anything. An earlier version of this check compared expiresAt against
  // the request's OWN createdAt — trivially bypassable, since an attacker
  // controlling both fields can place them arbitrarily far in the future
  // while keeping their difference inside the cap, making the code "look"
  // freshly issued no matter when it's actually redeemed (e.g.
  // createdAt = now+364d, expiresAt = now+364d+1h — passes a
  // createdAt-relative check, but the code stays "valid" for the next
  // year). Anchoring to THIS CALL's real wall clock instead closes that:
  // a request cannot claim to remain valid more than MAX_REQUEST_TTL_SEC
  // from right now, independent of what it claims createdAt to be.
  // createdAt itself is otherwise purely informational — never used for
  // any security decision here.
  if (expiresAtMs - Date.now() > MAX_REQUEST_TTL_SEC * 1000) {
    throw new Error('pairing request: expiry window exceeds the maximum this package allows')
  }

  return request
}
