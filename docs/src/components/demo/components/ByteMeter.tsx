// QR byte-mode ceilings (version 40, the largest QR symbol), by error-
// correction level — the SDK does not encode against a ceiling, it just
// `JSON.stringify`s (see `protocol/proposal.ts`), so the demo has to be the
// one to say when a payload has left "actually scannable" territory.
const QR_MAX_BYTES_ECC_L = 2953
// A phone camera at typical screen size gives up well before the
// theoretical max — measured empirically against this package's own
// proposal payloads (see CLAUDE.md for the measured sizes).
const PRACTICAL_SCAN_CEILING = 1200

export function byteLength(payload: string): number {
  return new TextEncoder().encode(payload).byteLength
}

export function ByteMeter({ bytes }: { bytes: number }) {
  const pct = Math.min(100, (bytes / QR_MAX_BYTES_ECC_L) * 100)
  const overPractical = bytes > PRACTICAL_SCAN_CEILING
  const overCeiling = bytes > QR_MAX_BYTES_ECC_L

  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between font-mono text-[11px]">
        <span
          className={
            overCeiling
              ? "text-danger"
              : overPractical
                ? "text-node-required"
                : "text-wire-muted"
          }
        >
          {bytes.toLocaleString()} bytes
        </span>
        <span className="text-wire-muted">
          ceiling {QR_MAX_BYTES_ECC_L.toLocaleString()} · practical scan ~
          {PRACTICAL_SCAN_CEILING.toLocaleString()}
        </span>
      </div>
      <div className="h-1 w-full bg-wire-rule">
        <div
          className={
            overCeiling
              ? "h-full bg-danger"
              : overPractical
                ? "h-full bg-node-required"
                : "h-full bg-live"
          }
          style={{ width: `${pct}%` }}
        />
      </div>
      {overCeiling ? (
        <p className="font-mono text-[11px] text-danger">
          over the QR ceiling — this payload cannot be encoded as a scannable
          code. Use copy-to-clipboard instead.
        </p>
      ) : overPractical ? (
        <p className="font-mono text-[11px] text-node-required">
          past where most phone cameras reliably scan. Dense but technically
          valid — copy-to-clipboard is the safer path.
        </p>
      ) : null}
    </div>
  )
}
