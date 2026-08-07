import {
  deriveBip44PrivateKey,
  deriveEvmAddress,
  deriveRoot,
  isEvmPrivateKey,
  normalizeEvmPrivateKey,
  registerDerivationScheme,
} from "@drakkar.software/octobot-client/identity"
import { useCallback, useEffect, useRef, useState } from "react"
import { CodeBlock } from "../components/CodeBlock"
import { Section } from "../components/Section"
import { bytesToHex, hexToBytes } from "../lib/hex"
import { useWalletKey } from "../lib/walletKeyContext"

type Rung = {
  key: string
  label: string
  detail: string
  status: "pending" | "running" | "done"
  value?: string
  ms?: number
}

const INITIAL_RUNGS: Rung[] = [
  {
    key: "privkey",
    label: "Private key",
    detail:
      "0x-prefixed, 64 hex chars, secp256k1 scalar in [1, n-1] — used as-is, nothing to derive",
    status: "pending",
  },
  {
    key: "address",
    label: "EIP-55 address",
    detail: "secp256k1 pubkey → keccak256 → checksum",
    status: "pending",
  },
  {
    key: "root",
    label: "Starfish root identity",
    detail:
      "EIP-191 sign('octobot:sync-bootstrap') → HKDF-expand → Ed25519 + X25519",
    status: "pending",
  },
  {
    key: "userid",
    label: "userId",
    detail: "hex(sha256(rootEdPub)).slice(0, 32)",
    status: "pending",
  },
]

// Registered once, locally, purely so the wrong-scheme toggle has something
// real to compare against. This scheme does NOT ship with the SDK — 'bip44'
// is the only built-in. A raw private key has nothing for a scheme to derive
// (bip44 passes it through unchanged), so the only way a second scheme can
// produce a genuinely different identity from the SAME key is to transform
// the key material itself — this hashes it. That keeps it a legitimate
// DerivationScheme, just a hypothetical one, exactly the shape
// `registerDerivationScheme` exists for: a consumer adding support for a
// wallet type the SDK doesn't ship.
let hypotheticalRegistered = false
function ensureHypotheticalScheme() {
  if (hypotheticalRegistered) return
  try {
    registerDerivationScheme({
      id: "demo-hypothetical",
      derive: async (privateKeyHex) => {
        const normalized = normalizeEvmPrivateKey(privateKeyHex)
        const digest = await crypto.subtle.digest(
          "SHA-256",
          hexToBytes(normalized) as Uint8Array<ArrayBuffer>,
        )
        return normalizeEvmPrivateKey(bytesToHex(new Uint8Array(digest)))
      },
    })
  } catch {
    // Vite HMR re-executes this module (resetting the flag above) without
    // resetting the SDK's own registry, which lives in a different,
    // non-hot-reloaded module — "already registered" then just means a
    // prior hot-reload already did this, which is fine.
  }
  hypotheticalRegistered = true
}

async function timed<T>(
  fn: () => Promise<T> | T,
): Promise<{ value: T; ms: number }> {
  const start = performance.now()
  const value = await fn()
  return { value, ms: performance.now() - start }
}

export function DerivationHero() {
  const { privateKey, setPrivateKey, regenerate } = useWalletKey()
  const [customKeyOpen, setCustomKeyOpen] = useState(false)
  const [customKeyDraft, setCustomKeyDraft] = useState("")
  const [customKeyError, setCustomKeyError] = useState<string | null>(null)
  const [rungs, setRungs] = useState<Rung[]>(INITIAL_RUNGS)
  const [fullHash, setFullHash] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)
  const [requestCount, setRequestCount] = useState(0)
  const [compareUserId, setCompareUserId] = useState<string | null>(null)
  const [showCompare, setShowCompare] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const runIdRef = useRef(0)

  // useCallback with an empty dep array, not a plain closure: `run` closes
  // over nothing reactive (only stable setState functions and the stable
  // runIdRef), so this reference never changes across renders. That makes
  // including `run` in the mount effect's deps below both correct AND safe
  // — no biome-ignore fighting the exhaustive-deps autofixer, which would
  // otherwise keep re-adding `run` to a plain closure's deps and reintroduce
  // a re-derive-every-render loop.
  const run = useCallback(async (key: string) => {
    const runId = ++runIdRef.current
    setIsRunning(true)
    setRungs(INITIAL_RUNGS.map((r) => ({ ...r })))
    setFullHash(null)
    setUserId(null)
    setCompareUserId(null)

    // Prove the "no network" claim rather than assert it: count every fetch
    // issued while this pipeline runs. It should never move. Two overlapping
    // runs (e.g. React StrictMode's double effect-invoke) would otherwise
    // each save/restore window.fetch independently and corrupt each other's
    // patch — the isRunning guard on the only other caller (the custom-key
    // button) prevents a user-triggered overlap, and the `window.fetch ===
    // patchedFetch` check below means a stale run's cleanup can never stomp
    // a newer run's still-active patch or restore a dead closure.
    const originalFetch = window.fetch
    let count = 0
    const patchedFetch = ((...args: Parameters<typeof fetch>) => {
      count += 1
      setRequestCount(count)
      return originalFetch(...args)
    }) as typeof fetch
    window.fetch = patchedFetch

    try {
      const step1 = await timed(() => deriveBip44PrivateKey(key))
      if (runIdRef.current !== runId) return
      setRungs((prev) =>
        prev.map((r) =>
          r.key === "privkey"
            ? { ...r, status: "done", value: step1.value, ms: step1.ms }
            : r,
        ),
      )

      const step2 = await timed(() => deriveEvmAddress(hexToBytes(step1.value)))
      if (runIdRef.current !== runId) return
      setRungs((prev) =>
        prev.map((r) =>
          r.key === "address"
            ? { ...r, status: "done", value: step2.value, ms: step2.ms }
            : r,
        ),
      )

      const step3 = await timed(() => deriveRoot(key, "bip44"))
      if (runIdRef.current !== runId) return
      setRungs((prev) =>
        prev.map((r) =>
          r.key === "root"
            ? {
                ...r,
                status: "done",
                value: step3.value.keys.edPub,
                ms: step3.ms,
              }
            : r,
        ),
      )

      const step4 = await timed(async () => {
        // TS 5.7+ makes Uint8Array generic over ArrayBufferLike; WebCrypto
        // wants the concrete ArrayBuffer variant (same cast the SDK's own
        // mnemonic.ts uses for the same reason).
        const digest = await crypto.subtle.digest(
          "SHA-256",
          hexToBytes(step3.value.keys.edPub) as Uint8Array<ArrayBuffer>,
        )
        return bytesToHex(new Uint8Array(digest))
      })
      if (runIdRef.current !== runId) return
      setFullHash(step4.value)
      setUserId(step3.value.userId)
      setRungs((prev) =>
        prev.map((r) =>
          r.key === "userid"
            ? { ...r, status: "done", value: step3.value.userId, ms: step4.ms }
            : r,
        ),
      )
    } finally {
      // Only restore if nothing else has already changed window.fetch away
      // from the patch THIS run installed — a stale run's cleanup must
      // never clobber a newer run's active patch or restore a dead closure.
      if (window.fetch === patchedFetch) window.fetch = originalFetch
      if (runIdRef.current === runId) setIsRunning(false)
    }
  }, [])

  // Re-derives whenever the shared wallet key changes — including when
  // QueuePanel/ProposePanel are reading the SAME key below, this is the one
  // place that key can be edited (via "use your own instead"), so this
  // effect is what keeps the reduction on screen honest after an edit, not
  // just on first mount.
  useEffect(() => {
    void run(privateKey)
  }, [privateKey, run])

  const onCompare = async () => {
    if (!privateKey) return
    ensureHypotheticalScheme()
    setShowCompare(true)
    const root = await deriveRoot(privateKey, "demo-hypothetical")
    setCompareUserId(root.userId)
  }

  const onUseCustomKey = async () => {
    // Guards the only other caller of run() — prevents a user submitting a
    // custom key while the initial (or a prior custom) derivation is still
    // in flight, which is what would otherwise race two overlapping
    // window.fetch patches (see the finally block in run()).
    if (isRunning) return
    const key = customKeyDraft.trim()
    if (!key) return
    if (!isEvmPrivateKey(key)) {
      setCustomKeyError(
        "not a valid private key — expected 0x followed by 64 hex characters",
      )
      return
    }
    const normalized = normalizeEvmPrivateKey(key)
    setCustomKeyError(null)
    setPrivateKey(normalized)
    setCustomKeyOpen(false)
    setShowCompare(false)
    await run(normalized)
  }

  const allDone = rungs.every((r) => r.status === "done")

  return (
    <Section
      id="derive"
      eyebrow="the wallet is the identity"
      title="A key becomes an identity, one real step at a time"
      weight="hero"
    >
      <p className="mb-8 max-w-2xl text-[15px] leading-relaxed text-wire-muted">
        Every read this SDK ever makes goes to{" "}
        <code className="font-mono text-wire-ink">
          users/&#123;userId&#125;/…
        </code>{" "}
        — and <code className="font-mono text-wire-ink">userId</code> is not the
        wallet address. It's derived, deterministically, from a chain that runs
        entirely in this tab. No node involved yet.
      </p>

      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-none border border-wire-rule bg-wire-surface px-4 py-3">
        <span className="font-mono text-[11px] uppercase tracking-wider text-wire-muted">
          requests sent while deriving
        </span>
        <span
          className={`font-mono text-lg tabular-nums ${requestCount === 0 ? "text-live" : "text-danger"}`}
        >
          {requestCount}
        </span>
        <span className="font-mono text-[11px] text-wire-muted">
          — check devtools' network tab if you don't believe it
        </span>
      </div>

      <div className="mb-6 rounded-none border border-wire-rule bg-wire-surface p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            private key
          </span>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={regenerate}
              className="font-mono text-[11px] text-wire-muted underline decoration-dotted underline-offset-2 hover:text-live"
            >
              regenerate
            </button>
            <button
              type="button"
              onClick={() => setCustomKeyOpen((v) => !v)}
              className="font-mono text-[11px] text-wire-muted underline decoration-dotted underline-offset-2 hover:text-live"
            >
              use your own instead
            </button>
          </div>
        </div>
        <p className="break-all font-mono text-[13px] text-wire-ink">
          {privateKey || "generating…"}
        </p>
        <p className="mt-2 font-mono text-[11px] text-wire-muted">
          a throwaway demo key kept in this browser's localStorage — reload and
          it's still the same identity. Never sent anywhere — see the counter
          above. Hit "regenerate" for a fresh one.
        </p>
        {customKeyOpen ? (
          <div className="mt-4 border-t border-wire-rule pt-4">
            <textarea
              value={customKeyDraft}
              onChange={(e) => {
                setCustomKeyDraft(e.target.value)
                setCustomKeyError(null)
              }}
              placeholder="your own 0x… private key — stays in this tab, same as above"
              rows={2}
              className="w-full resize-none rounded-none border border-wire-rule bg-wire-bg px-3 py-2 font-mono text-[13px] text-wire-ink placeholder:text-wire-muted/60 focus:outline-none"
            />
            {customKeyError ? (
              <p className="mt-2 font-mono text-[11px] text-danger">
                {customKeyError}
              </p>
            ) : null}
            <button
              type="button"
              onClick={onUseCustomKey}
              disabled={isRunning}
              className="mt-2 rounded-none border border-live px-3 py-1.5 font-mono text-[12px] text-live hover:bg-live/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isRunning ? "deriving…" : "derive this instead"}
            </button>
          </div>
        ) : null}
      </div>

      <ol className="space-y-3">
        {rungs.map((rung, i) => (
          <li
            key={rung.key}
            className={`flex flex-col gap-1 border-l-2 py-2 pl-4 transition-colors ${
              rung.status === "done"
                ? "border-live"
                : rung.status === "running"
                  ? "border-wire-muted"
                  : "border-wire-rule"
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="font-mono text-[11px] text-wire-muted">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span
                className={`font-mono text-[13px] ${rung.status === "done" ? "text-wire-ink" : "text-wire-muted"}`}
              >
                {rung.label}
              </span>
              {rung.ms !== undefined ? (
                <span className="font-mono text-[11px] text-wire-muted">
                  {rung.ms.toFixed(1)}ms
                </span>
              ) : null}
            </div>
            <span className="pl-6 font-mono text-[11px] text-wire-muted">
              {rung.detail}
            </span>
            {rung.value ? (
              <span className="break-all pl-6 font-mono text-[12px] text-live">
                {rung.key === "userid" ? rung.value : rung.value}
              </span>
            ) : null}
          </li>
        ))}
      </ol>

      {allDone && fullHash && userId ? (
        <div className="mt-8 border-t border-wire-rule pt-6">
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            sha256(rootEdPub) — full digest, then the surviving 32 hex
            characters
          </p>
          <p className="break-all font-mono text-[15px] leading-relaxed">
            <span className="text-live">{fullHash.slice(0, 32)}</span>
            <span className="text-wire-rule">{fullHash.slice(32)}</span>
          </p>
          <p className="mt-4 font-mono text-[13px] text-wire-muted">
            → <span className="text-wire-ink">users/{userId}/accounts</span>
            <span className="ml-2 text-wire-muted">
              {" "}
              ← the literal path every read below uses
            </span>
          </p>

          <div className="mt-6 border-t border-wire-rule pt-6">
            <button
              type="button"
              onClick={onCompare}
              className="font-mono text-[12px] text-wire-muted underline decoration-dotted underline-offset-2 hover:text-node-required"
            >
              what if the wrong scheme were picked?
            </button>
            {showCompare && compareUserId ? (
              <div className="mt-3 space-y-1 font-mono text-[12px]">
                <p className="text-wire-muted">
                  same key, a hypothetical alternate scheme registered locally
                  for this demo (not shipped by the SDK):
                </p>
                <p>
                  <span className="text-wire-muted">bip44 → </span>
                  <span className="text-live">{userId}</span>
                </p>
                <p>
                  <span className="text-wire-muted">demo-hypothetical → </span>
                  <span className="text-node-required">{compareUserId}</span>
                </p>
                <p className="mt-2 text-danger">
                  two different identities, two disjoint sets of synced data.
                  Pick the wrong one against a real node and every call still
                  succeeds — it just authenticates as a wallet the node has
                  never seen. Reads come back empty, not with an error.
                </p>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="mt-8">
        <CodeBlock
          language="ts"
          code={`import { deriveBip44PrivateKey, deriveEvmAddress, deriveRoot } from '@drakkar.software/octobot-client/identity'

const privateKey = await deriveBip44PrivateKey(rawPrivateKeyHex) // a raw key passes straight through unchanged
const address = deriveEvmAddress(hexToBytes(privateKey))         // EIP-55 checksummed
const root = await deriveRoot(rawPrivateKeyHex, 'bip44')         // signs the bootstrap challenge, HKDF-expands
console.log(root.userId)                                         // hex(sha256(root.keys.edPub)).slice(0, 32)`}
        />
      </div>
    </Section>
  )
}
