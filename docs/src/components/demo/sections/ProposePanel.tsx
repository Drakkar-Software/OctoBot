import {
  connectReadOnlyDevice,
  createReadOnlyPairing,
  type ReadOnlyOctoBotClient,
} from "@drakkar.software/octobot-client"
import {
  buildStopAutomationConfig,
  encodeActionProposal,
} from "@drakkar.software/octobot-client/protocol"
import {
  type NodeEndpoint,
  parseHostInput,
} from "@drakkar.software/octobot-client/transport"
import { QRCodeSVG } from "qrcode.react"
import { useEffect, useMemo, useState } from "react"
import { ByteMeter, byteLength } from "../components/ByteMeter"
import { CodeBlock } from "../components/CodeBlock"
import { Section } from "../components/Section"
import { useNodeUrl } from "../lib/nodeUrlContext"
import { useWalletKey } from "../lib/walletKeyContext"

// Same automation id used by both proposal paths below, so the two are a
// fair side-by-side comparison of the same write call.
const DEMO_AUTOMATION_ID = "demo-automation-id"

// ByteMeter doesn't export its thresholds, so they're mirrored here to
// decide whether a QR is even safe to attempt (past the hard ceiling
// QRCodeSVG throws) and when "copy JSON" should stop being a footnote and
// become the primary action.
const QR_HARD_CEILING = 2953
const PRACTICAL_SCAN_CEILING = 1200

type ProposalPath = "offline" | "connected"

/**
 * The one scoped light inversion on this page. `bg-paper-bg` +
 * `text-paper-ink` (via `currentColor`, since QRCodeSVG takes color props,
 * not classes) are the only tokens used inside — no border, no shadow, no
 * rounded corners, just a flat rectangle with a hard edge. Nothing lives in
 * here but the QR module itself; the byte count and scan hint are rendered
 * by the caller, outside this box.
 */
function PayloadQrZone({
  payload,
  scanHint,
}: {
  payload: string
  scanHint: string
}) {
  const bytes = byteLength(payload)
  const overPractical = bytes > PRACTICAL_SCAN_CEILING
  const overHardCeiling = bytes > QR_HARD_CEILING
  const [copied, setCopied] = useState(false)

  const onCopy = () => {
    void navigator.clipboard.writeText(payload).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className="space-y-2">
      <ByteMeter bytes={bytes} />
      {overHardCeiling ? (
        <button
          type="button"
          onClick={onCopy}
          className="w-full border border-danger px-3 py-2 font-mono text-[12px] text-danger hover:bg-danger/10"
        >
          {copied ? "copied" : "copy JSON — too large to render as a QR"}
        </button>
      ) : (
        <>
          <div className="flex justify-center bg-paper-bg p-4 text-paper-ink">
            <QRCodeSVG
              value={payload}
              size={220}
              bgColor="transparent"
              fgColor="currentColor"
            />
          </div>
          {overPractical ? (
            <div className="flex flex-col gap-2">
              <span className="font-mono text-[11px] text-wire-muted">
                {scanHint}
              </span>
              <button
                type="button"
                onClick={onCopy}
                className="w-full border border-node-required px-3 py-2 font-mono text-[12px] text-node-required hover:bg-node-required/10"
              >
                {copied
                  ? "copied"
                  : "copy JSON — safer than scanning at this size"}
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] text-wire-muted">
                {scanHint}
              </span>
              <button
                type="button"
                onClick={onCopy}
                className="font-mono text-[11px] text-wire-muted hover:text-live"
              >
                {copied ? "copied" : "copy JSON"}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export function ProposePanel() {
  const { privateKey } = useWalletKey()
  const { url, setUrl } = useNodeUrl()
  const [minting, setMinting] = useState(false)
  const [mintError, setMintError] = useState<string | null>(null)
  const [pairingPayload, setPairingPayload] = useState<string | null>(null)
  const [readOnlyClient, setReadOnlyClient] =
    useState<ReadOnlyOctoBotClient | null>(null)

  const [path, setPath] = useState<ProposalPath>("offline")
  const [connectedPayload, setConnectedPayload] = useState<string | null>(null)
  const [connectedError, setConnectedError] = useState<string | null>(null)
  const [connectedLoading, setConnectedLoading] = useState(false)

  // Fully offline: no private key, no pairing, no network. The cheapest,
  // most honest "works with nothing running" proposal — always available.
  const offlinePayload = useMemo(() => {
    const configuration = buildStopAutomationConfig(DEMO_AUTOMATION_ID)
    return encodeActionProposal([{ configuration }], {
      label: `Stop automation ${DEMO_AUTOMATION_ID}`,
    })
  }, [])

  useEffect(() => {
    return () => readOnlyClient?.close()
  }, [readOnlyClient])

  useEffect(() => {
    if (!readOnlyClient) {
      setConnectedPayload(null)
      setConnectedError(null)
      return
    }
    let cancelled = false
    setConnectedLoading(true)
    setConnectedError(null)
    readOnlyClient.automations
      .stop(DEMO_AUTOMATION_ID)
      .then((proposed) => {
        if (!cancelled) setConnectedPayload(proposed.payload)
      })
      .catch((err) => {
        if (!cancelled)
          setConnectedError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setConnectedLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [readOnlyClient])

  const onMint = async () => {
    const parsed = parseHostInput(url)
    if (!parsed) {
      setMintError("enter a valid node url, e.g. http://192.168.1.10:5001")
      return
    }
    setMinting(true)
    setMintError(null)
    try {
      const node: NodeEndpoint = parsed
      const { payload } = await createReadOnlyPairing(privateKey, "bip44", node)
      setPairingPayload(payload)
      const client = await connectReadOnlyDevice(payload)
      setReadOnlyClient(client)
    } catch (err) {
      setMintError(err instanceof Error ? err.message : String(err))
    } finally {
      setMinting(false)
    }
  }

  const activePayload = path === "offline" ? offlinePayload : connectedPayload

  const offlineCode = `import { buildStopAutomationConfig, encodeActionProposal } from '@drakkar.software/octobot-client/protocol'

const configuration = buildStopAutomationConfig('${DEMO_AUTOMATION_ID}')
const payload = encodeActionProposal([{ configuration }], { label: 'Stop automation ${DEMO_AUTOMATION_ID}' })
// payload is JSON.stringify under the hood, nothing more — render it as a QR, or copy it`

  const connectedCode = `import { connectReadOnlyDevice } from '@drakkar.software/octobot-client'

const octobot = await connectReadOnlyDevice(pairingPayload)               // bearer cap, no private key
const proposed = await octobot.automations.stop('${DEMO_AUTOMATION_ID}')  // builds the action, never appends it
console.log(proposed.payload)                                             // render this as a QR`

  return (
    <Section
      id="propose"
      eyebrow="the less-trusted client"
      title="What a device holding only this payload can do"
      weight="normal"
    >
      <div className="mb-8 max-w-2xl space-y-3 text-[15px] leading-relaxed text-wire-muted">
        <p>
          A read-only pairing payload carries a bearer credential for one device
          — never the wallet's private key. Reads behave exactly like a
          privileged client:{" "}
          <code className="font-mono text-wire-ink">accounts.list()</code>,{" "}
          <code className="font-mono text-wire-ink">automations.list()</code>{" "}
          pull straight from the node. Every write —{" "}
          <code className="font-mono text-wire-ink">create</code>,{" "}
          <code className="font-mono text-wire-ink">update</code>,{" "}
          <code className="font-mono text-wire-ink">delete</code>,{" "}
          <code className="font-mono text-wire-ink">refresh</code>,{" "}
          <code className="font-mono text-wire-ink">stop</code> — takes a
          different path: it builds the action(s) locally and hands back a{" "}
          <code className="font-mono text-wire-ink">ProposedAction</code>{" "}
          instead of sending it.
        </p>
        <p className="text-wire-ink">
          This scoping is enforced client-side today, not by the node. The node
          currently authorizes every collection by identity alone —{" "}
          <code className="font-mono text-wire-muted">
            connectReadOnlyDevice()
          </code>
          's write methods simply never call the node's append endpoint on this
          session's behalf. Treat this payload as "read, and propose", not yet
          as a boundary the node itself checks.
        </p>
      </div>

      <div className="mb-8 border border-wire-rule bg-wire-surface p-4">
        <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
          mint a read-only pairing
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex min-w-[220px] flex-1 flex-col gap-1">
            <span className="font-mono text-[11px] text-wire-muted">
              node url
            </span>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="http://localhost:5001"
              className="w-full border border-wire-rule bg-wire-bg px-2 py-1.5 font-mono text-[13px] text-wire-ink placeholder:text-wire-muted/50 focus:outline-none"
            />
          </label>
          <button
            type="button"
            onClick={() => void onMint()}
            disabled={minting}
            className="border border-live px-3 py-1.5 font-mono text-[12px] text-live hover:bg-live/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {minting ? "minting…" : "mint a read-only pairing"}
          </button>
        </div>
        <p className="mt-2 font-mono text-[11px] text-wire-muted">
          the same url and wallet as the connect panel above — never sent
          anywhere, only used locally to sign the pairing.
        </p>
        {mintError ? (
          <p className="mt-2 font-mono text-[11px] text-danger">{mintError}</p>
        ) : null}

        {pairingPayload ? (
          <div className="mt-4 border-t border-wire-rule pt-4">
            <PayloadQrZone
              payload={pairingPayload}
              scanHint={
                readOnlyClient
                  ? "scan with another device to start a read-only session — connected below"
                  : "scan with another device to start a read-only session"
              }
            />
          </div>
        ) : null}
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setPath("offline")}
          className={`border px-3 py-1.5 font-mono text-[12px] ${
            path === "offline"
              ? "border-live text-live"
              : "border-wire-rule text-wire-muted hover:text-wire-ink"
          }`}
        >
          offline · buildStopAutomationConfig
        </button>
        <button
          type="button"
          onClick={() => setPath("connected")}
          disabled={!readOnlyClient}
          className={`border px-3 py-1.5 font-mono text-[12px] disabled:cursor-not-allowed disabled:opacity-40 ${
            path === "connected"
              ? "border-live text-live"
              : "border-wire-rule text-wire-muted hover:text-wire-ink"
          }`}
        >
          connected · client.automations.stop()
        </button>
      </div>

      {path === "connected" && !readOnlyClient ? (
        <p className="mb-8 font-mono text-[12px] text-node-required">
          mint a pairing above first — this tab previews the same proposal built
          by a connected read-only client.
        </p>
      ) : connectedError ? (
        <p className="mb-8 font-mono text-[12px] text-danger">
          {connectedError}
        </p>
      ) : connectedLoading && !activePayload ? (
        <p className="mb-8 font-mono text-[12px] text-wire-muted">
          building proposal…
        </p>
      ) : activePayload ? (
        <div className="mb-8">
          <PayloadQrZone
            payload={activePayload}
            scanHint={`stop automation "${DEMO_AUTOMATION_ID}" — a privileged device scans this and executes it after review`}
          />
        </div>
      ) : null}

      <CodeBlock
        language="ts"
        code={path === "offline" ? offlineCode : connectedCode}
      />
    </Section>
  )
}
