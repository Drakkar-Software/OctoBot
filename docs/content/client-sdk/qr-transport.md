---
title: "QR Transport"
description: "Split an oversized payload across a cycling sequence of scannable QR frames, and reassemble it on the scanning side, without the codec knowing anything about what it carries."
sidebar_position: 15
---

# QR transport

Two of this package's payloads are handed between devices as a QR code: a
[read-only pairing payload](read-only-pairing.md) and an action proposal. Neither is guaranteed to
fit in one code.

A QR at version 11 with error-correction level M, a common library default, holds 251 bytes. A
proposal from `automations.create()` carries two full action configurations and runs to several
thousand. A read-only pairing payload is around 1.2 KB. Encoded as a single code those still
"work", in the sense that a QR library will produce an image, but the image is two to three times
denser than a phone camera reads comfortably at a typical on-screen size.

`protocol/qrFrames.ts` is the answer: split the payload into a sequence of frames, cycle them on
screen, and reassemble on the other side.

```ts
import { encodeQrFrames, createQrFrameAccumulator } from '@drakkar.software/octobot-client/protocol'
```

## The codec knows nothing about the payload

Plain string in, plain string out. `encodeQrFrames` never parses what it is given, and the
accumulator hands back exactly the bytes that went in.

That is the whole point. A reassembled payload goes back through `classifyScannedCode` like any
single-frame scan, so nothing downstream has to learn a second code path, and a new payload type
becomes framable without touching this module at all.

## Wire format

```
OBQR2|<kind>|<transferId>|<index>|<total>|<body>
```

| Field | Width | Notes |
|---|---|---|
| `OBQR2` | 5 | Codec token. |
| `<kind>` | 1 | Advisory tag, `[A-Za-z-]`. See below. |
| `<transferId>` | 8 | First 4 bytes of `keccak256(payload)`, lower-case hex. |
| `<index>` | 2 | Zero-padded, zero-based. |
| `<total>` | 2 | Zero-padded frame count. |

The header is a constant 23 bytes, which matters: the body is recovered with a fixed `slice`, never
a `split('|')`. Bodies are usually JSON and contain `|` freely.

`transferId` is a hash of the payload rather than a random id, so it needs no RNG and doubles as an
integrity check. If the reassembled string does not hash back to it, the transfer is reported
corrupt rather than handed on.

| Constant | Value | Meaning |
|---|---|---|
| `QR_FRAME_MAX_BYTES` | 240 | Whole-frame ceiling, including the header. |
| `QR_FRAME_BODY_MAX_BYTES` | 217 | What is left for the body. |
| `QR_SINGLE_FRAME_MAX_BYTES` | 300 | At or below this, nothing is framed. |
| `QR_MAX_FRAMES` | 99 | ~21.4 KB of ASCII; less for wider code points (see below). |
| `QR_FRAME_INTERVAL_MS` | 250 | Suggested cycling cadence. |

## Producing

```ts
const payload = encodeActionProposal(actions, { label })
const frames = encodeQrFrames(payload, { kind: QR_FRAME_KIND_ACTION_PROPOSAL })
// render frames[i], advancing i every QR_FRAME_INTERVAL_MS
```

A payload at or below `QR_SINGLE_FRAME_MAX_BYTES` comes back as `[payload]`, unchanged and with no
header, so a short code renders exactly as it would without this module. Check `frames.length > 1`
to decide whether to show a progress indicator at all.

Above `QR_MAX_FRAMES`, `encodeQrFrames` throws `QrPayloadTooLargeError`, carrying `requiredFrames`
and `maxFrames` so a caller can say something more useful than "failed".

**Encode once, then leave it alone.** `encodeActionProposal` stamps a fresh `createdAt` on every
call, and a frame's `transferId` hashes the payload. Re-encoding mid-transfer therefore changes
every frame and the id, and a scanner part-way through discards everything it had collected. Hold
the encoded frames in state keyed on the proposal, not on anything that changes when the screen
re-renders.

Frames are split to an even byte share rather than greedily packed, so the last frame is not
visibly sparser than the rest. A code that changes density as it cycles sends a scanner's autofocus
hunting. Splitting is by UTF-8 **bytes**, not characters, and cuts land on code-point boundaries,
so a surrogate pair is never severed and a CJK or accented payload cannot overflow a frame that an
ASCII test would have passed.

Because a frame can only end on a code-point boundary, a payload of wide code points cannot fill
every frame to the full 217 bytes: 4-byte code points cap a body at 216. The practical ceiling is
therefore a little under `QR_MAX_FRAMES * QR_FRAME_BODY_MAX_BYTES` for anything but ASCII, and
`QrPayloadTooLargeError.requiredFrames` reports what the payload actually needs.

## Consuming

One accumulator per scanner instance, never a module singleton.

```ts
const acc = createQrFrameAccumulator()

function onBarcode(data: string) {
  const r = acc.accept(data)
  switch (r.status) {
    case 'ignored':    return classifyScannedCode(data)  // not ours, or a refused kind
    case 'discarded':  return                            // our garbage: drop, stay armed
    case 'progress':
    case 'restarted':  return showProgress(r.progress)
    case 'corrupt':    return                            // producer is still cycling, it refills
    case 'complete':   return classifyScannedCode(r.payload)
  }
}
```

The six statuses are the whole contract:

- **`ignored`** is not a frame of this codec at all, or a frame whose kind `acceptKind` refused.
  Nothing was buffered. Classify it yourself.
- **`discarded`** matched the `OBQR2|` prefix but failed to parse. That is *our* malformed output,
  not an unknown code, so drop it silently rather than reporting an unrecognized scan.
- **`progress`** accepted a frame. Duplicates are the normal case, since a 30fps camera reads the
  same displayed frame several times before it cycles, and they leave the count unchanged.
- **`restarted`** means a different transfer interrupted this one, or the previous one went stale.
  The old buffer is gone.
- **`corrupt`** means every frame arrived but the payload did not hash back to `transferId`.
  Recovery is usually silent: the producer is still cycling and refills within one more pass.
- **`complete`** fires exactly once per transfer. Internal state resets before it returns.

A transfer with no new frame for `staleMs` (8 seconds by default) is dropped, so a walked-away-from
transfer cannot poison the next one. Note the accumulator only re-checks staleness on the next
`accept` call, so a UI that needs a stalled progress bar to clear on its own needs its own timer.

## The kind tag

Every frame carries one character naming what the transfer is: `QR_FRAME_KIND_ACTION_PROPOSAL`
(`p`), `QR_FRAME_KIND_READ_ONLY_PAIRING` (`r`), or `QR_FRAME_KIND_UNSPECIFIED` (`-`), the default.

It is advisory. The codec never reads the body and never checks that the tag is honest, and a
scanner that accepts everything can ignore it entirely.

It earns its two bytes on a **single-purpose** scanner. An onboarding screen that only ever accepts
a pairing payload can refuse anything else at its first frame:

```ts
const acc = createQrFrameAccumulator({
  acceptKind: (kind) => kind === QR_FRAME_KIND_READ_ONLY_PAIRING,
})
```

A refused kind returns `ignored` and buffers nothing, so the scanner never fills up with a
transfer it was going to reject anyway, and an unrelated producer cycling nearby cannot stall it.
Without the tag that decision is impossible until reassembly finishes.

**`acceptKind` is buffer hygiene, not a type gate.** Two limits matter, and a caller that treats it
as a security or routing control will be wrong about both:

- The tag is unauthenticated and never checked against the body. Nothing stops a producer tagging
  an action proposal as `r`. That is why `complete` deliberately does not report the kind: the
  payload's real type is whatever `classifyScannedCode` says after reassembly, always.
- A payload at or below `QR_SINGLE_FRAME_MAX_BYTES` is never framed, carries no tag, and so is
  never subject to `acceptKind` at all. It arrives as `ignored` and goes to `classifyScannedCode`
  like any other unrecognized scan, which is the full classification surface. Filtering framed
  transfers narrows nothing about what a short payload can be.

## What this does not do

**It provides integrity, never authenticity.** `transferId` is a truncated hash of the payload,
carried alongside the payload it hashes, so it detects a garbled or spliced reassembly. It says
nothing about who produced the frames: an entirely attacker-generated transfer reassembles to
`complete` with no work at all. Read `complete` as "not garbled", never as "trustworthy". Nothing
downstream treats it otherwise; `decodeActionProposal` and `parseReadOnlyPairing` are both purely
structural, and trust comes from the human confirming what the QR turned out to contain.

**A framed QR is secret material for as long as it cycles.** An action proposal can carry exchange
API keys, passphrases and seed phrases as plaintext JSON, and a pairing payload carries capability
certificates and per-collection keys. Framing changes the exposure profile in both directions: a
single photograph now yields one fragment rather than the whole secret, but the code must stay on
screen for at least a full cycle, which is seconds for a large proposal rather than the instant a
static code needs. Treat the displaying screen accordingly: suppress screenshots (`FLAG_SECURE` on
Android, screen-capture suppression on iOS), dismiss it when the hand-off is done, and warn against
screen sharing.

This package never renders a QR image, here as everywhere else. It returns the strings to encode
and consumes the strings a scanner read. Pick your own QR library, and size the display so a
61-module code stays comfortable, which is what the 240-byte frame ceiling targets.
