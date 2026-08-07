import useDocusaurusContext from "@docusaurus/useDocusaurusContext"
import {
  attemptDirectMirrorWrite,
  awaitPairingGrant,
  fetchPairingGrant,
  fetchPairingRequestByCode,
  type MintedPairingGrant,
  mintPairingGrant,
  type PairingRequestPayload,
  type PairingRequestSession,
  publishPairingGrant,
  startPairingRequest,
  syncCloudMirror,
  type UnsealedPairingGrant,
} from "@drakkar.software/octobot-client"
import { deriveRoot } from "@drakkar.software/octobot-client/identity"
import {
  buildSession,
  defaultSpaceLayout,
  type Session,
  type SpaceLayout,
} from "@drakkar.software/starfish-spaces"
import { useEffect, useState } from "react"
import { CodeBlock } from "../components/CodeBlock"
import { Section } from "../components/Section"
import { generateRandomPrivateKey } from "../lib/randomKey"

// The real shared Drakkar sync server — the `joinsessions` collection this
// flow needs is deployed and public read/write there. Overridable for a
// local/staging sync server via `docusaurus.config.ts`'s
// `customFields.rendezvous` (Docusaurus has no build-time env-var
// passthrough equivalent to Vite's `import.meta.env`).
function useRendezvous() {
  const { siteConfig } = useDocusaurusContext()
  const custom = siteConfig.customFields?.rendezvous as
    | { baseUrl?: string; namespace?: string }
    | undefined
  return {
    baseUrl: custom?.baseUrl ?? "https://prod-sync.drakkar.software/sync",
    namespace: custom?.namespace ?? "dk",
  }
}

// `defaultSpaceLayout.accountScope` scopes the account-level cap to
// `collections: ['*']`. The deployed sync server's cap resolver does NOT
// expand that wildcard — a collection whose own role check expects
// `cap:read:spaces` literally never matches a cap synthesizing `cap:read:*`,
// so a stock account cap 403s on its very first `readSpaces()` call. The real
// app (OctoBot Cloud's `octobot-sdk`'s `dkspaces/session.ts`) works around this with
// an explicit collection list; this is the same fix, scoped down to only what
// minting a mirror-pairing grant actually touches through the account client:
// `spaces` (`user/{id}/_spaces`, the joined-space registry) and
// `spaceregistry` (`spaces/{spaceId}/_access`, written by `createSpace` and
// `inviteToSpace`'s `addSpaceMember` before any space-level cap exists yet).
// Space CONTENT (the mirror nodes themselves) goes through the space-level
// cap instead, which `defaultSpaceLayout` already scopes to an explicit list
// rather than a wildcard — no override needed there.
const DEMO_SPACE_LAYOUT: SpaceLayout = {
  ...defaultSpaceLayout,
  accountScope: (userId) => ({
    ops: ["read", "write", "list"],
    collections: ["spaces", "spaceregistry"],
    paths: [`user/${userId}/**`, "spaces/**", `inbox/${userId}/**`],
  }),
}

// Fixture-shaped demo data the "phone" writes into its real mirror space —
// clearly labeled as such everywhere it's rendered, never presented as real
// synced data. `user-accounts`/`user-data` are the two collection ids this
// demo mirrors (accounts + automations — see `MIRROR_COLLECTIONS`), both
// third-party-eligible so a grant can actually cover them.
//
// Built from a live `btcAmount` (not a constant) so the "re-sync mirror"
// button below can push a genuinely different document on each click — the
// point of that button is proving `syncCloudMirror`/`fetchPairingGrant` are a
// real live read/write loop, not a one-shot snapshot, which the prose at the
// bottom of this section could previously only assert, not demonstrate.
function buildDemoAccountsDoc(btcAmount: number) {
  return {
    items: [
      {
        id: "acc-demo-1",
        name: "Binance (demo)",
        type: "exchange",
        exchange: "binance",
        simulated: true,
        connected: true,
        holdings: [
          { symbol: "BTC", total: btcAmount, free: btcAmount, used: 0 },
        ],
      },
    ],
  }
}

function buildDemoAutomationsDoc(btcAmount: number) {
  return {
    items: [
      {
        id: "auto-demo-1",
        name: "DCA into BTC (demo)",
        status: "live",
        accountIds: ["acc-demo-1"],
        strategy: { id: "strat-demo-1", version: "1.0.0" },
        assets: [{ symbol: "BTC", total: btcAmount, free: btcAmount, used: 0 }],
      },
    ],
  }
}

const DEMO_ENABLED_COLLECTIONS = ["user-accounts", "user-data"]

function buildReadDemoSourceCollection(
  btcAmount: number,
): (collectionId: string) => Promise<unknown> {
  return (collectionId: string) => {
    if (collectionId === "user-accounts")
      return Promise.resolve(buildDemoAccountsDoc(btcAmount))
    if (collectionId === "user-data")
      return Promise.resolve(buildDemoAutomationsDoc(btcAmount))
    return Promise.resolve({})
  }
}

type StepStatus = "pending" | "running" | "done" | "error"

function statusColor(status: StepStatus): string {
  if (status === "done") return "text-live"
  if (status === "error") return "text-danger"
  if (status === "running") return "text-node-required"
  return "text-wire-muted"
}

function StepRow({
  n,
  label,
  status,
  detail,
}: {
  n: number
  label: string
  status: StepStatus
  detail?: string
}) {
  return (
    <div
      className={`flex flex-col gap-1 border-l-2 py-2 pl-4 ${status === "pending" ? "border-wire-rule" : status === "error" ? "border-danger" : status === "done" ? "border-live" : "border-node-required"}`}
    >
      <div className="flex items-center gap-3">
        <span className="font-mono text-[11px] text-wire-muted">
          {String(n).padStart(2, "0")}
        </span>
        <span
          className={`font-mono text-[13px] ${status === "pending" ? "text-wire-muted" : "text-wire-ink"}`}
        >
          {label}
        </span>
        <span
          className={`font-mono text-[10px] uppercase tracking-wider ${statusColor(status)}`}
        >
          {status}
        </span>
      </div>
      {detail ? (
        <span className="break-all pl-6 font-mono text-[12px] text-wire-muted">
          {detail}
        </span>
      ) : null}
    </div>
  )
}

const WEBSITE_SNIPPET = `const session = await startPairingRequest({
  origin: window.location.origin,
  label: 'Demo Trading Dashboard',
  rendezvous: RENDEZVOUS,
  requestedCollections: ['accounts', 'userData'],
})
await session.publish()
// session.code is the real 8-character human code — what a real website
// would display for the user to type into their own OctoBot app.

// session already carries the rendezvous it was published to — no need to
// re-spread it at each call site.
const result = await awaitPairingGrant(session, { timeoutMs: 5 * 60_000 })
console.log(result.collections['user-accounts'], result.collections['user-data'])

// Poll again any time to see the latest write — this is a live read, not a
// one-time export.
const refreshed = await fetchPairingGrant(session, { expectedSealer: result.sealedBy })`

const PHONE_SNIPPET = `// Step 1 — look up the request the user typed the code for. Nothing is
// shared yet: this is only enough to show the user what they'd be
// approving. \`hash\` is the pulled document's hash — remember it, the
// grant write below needs it.
const { request: found, hash } = await fetchPairingRequestByCode({
  code: session.code,
  rendezvous: RENDEZVOUS,
})
// Show found.origin and found.label to the user for confirmation — do not
// proceed to step 2 without an explicit "approve" from them.

// Step 2 — only after the user approves: build (or reuse) a real spaces
// Session for the phone's own wallet, make sure the mirror actually has
// something to invite the site into, then mint + publish the grant.
const { userId, keys } = await deriveRoot(phonePrivateKey, 'bip44')
const session = await buildSession({
  userId, keys, clientOpts: SPACES_CLIENT_OPTS,
  autoProfile: false, config: { layout: DEMO_SPACE_LAYOUT },
})

await syncCloudMirror({
  session,
  enabledCollectionIds: ['user-accounts', 'user-data'],
  readSourceCollection: readDemoSourceCollection,
})

const grant = await mintPairingGrant(session, found)

await publishPairingGrant({
  request: found,
  sealer: { edPrivHex: keys.edPriv, edPubHex: keys.edPub },
  grant,
  rendezvous: RENDEZVOUS,
  // MUST be the request's own hash from step 1, not null — this slot
  // already holds the request doc, so this write is a compare-and-swap
  // claiming exactly the request that was read, not a "fresh slot" create.
  baseHash: hash,
})`

export function WebsitePairingSim() {
  const rendezvous = useRendezvous()
  // Same server/namespace the mirror space itself lives on — spaces are a
  // `dk`-namespace concept, same as the rendezvous above.
  const spacesClientOpts = { baseUrl: rendezvous.baseUrl, namespace: rendezvous.namespace }

  // Gates the whole simulation behind an explicit click: unlike the original
  // standalone demo, this section now renders on every visit to a docs page
  // — auto-firing `startPairingRequest` on mount would open a live 5-minute
  // wait against production sync for every reader, whether or not they ever
  // scroll this far.
  const [started, setStarted] = useState(false)

  const [websiteStatus, setWebsiteStatus] = useState<StepStatus>("pending")
  const [websiteError, setWebsiteError] = useState<string | null>(null)
  const [session, setSession] = useState<PairingRequestSession | null>(null)

  const [lookupStatus, setLookupStatus] = useState<StepStatus>("pending")
  const [lookupError, setLookupError] = useState<string | null>(null)
  const [foundRequest, setFoundRequest] =
    useState<PairingRequestPayload | null>(null)
  // The pulled request document's hash — required as `baseHash` on the
  // grant write below (a compare-and-swap claiming exactly this request),
  // not something the old sessionId-keyed design needed to track here.
  const [foundRequestHash, setFoundRequestHash] = useState<string | null>(
    null,
  )

  const [phoneKeyInput, setPhoneKeyInput] = useState("")

  const [shareStatus, setShareStatus] = useState<StepStatus>("pending")
  const [shareError, setShareError] = useState<string | null>(null)
  const [phoneUserId, setPhoneUserId] = useState<string | null>(null)
  const [phoneRootEdPub, setPhoneRootEdPub] = useState<string | null>(null)
  const [mintedGrant, setMintedGrant] = useState<MintedPairingGrant | null>(
    null,
  )

  const [resolveStatus, setResolveStatus] = useState<StepStatus>("pending")
  const [resolveError, setResolveError] = useState<string | null>(null)
  const [result, setResult] = useState<UnsealedPairingGrant | null>(null)

  // Kept around after "approve & share" so the "re-sync mirror" button below
  // can write to the SAME space again without re-deriving from the private
  // key input (which the user may have already cleared/changed).
  const [phoneSession, setPhoneSession] = useState<Session | null>(null)
  const [btcAmount, setBtcAmount] = useState(0.42)
  const [resyncStatus, setResyncStatus] = useState<StepStatus>("pending")
  const [resyncError, setResyncError] = useState<string | null>(null)
  const [lastSyncedAmount, setLastSyncedAmount] = useState<number | null>(null)

  const [refreshStatus, setRefreshStatus] = useState<StepStatus>("pending")
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null)

  // Website, step 5 (optional, repeatable): the cap this site holds is
  // read-only (`mintPairingGrant` always mints with `canWrite: false`), so
  // this is expected to fail every time — the point is to actually show
  // that rejection instead of only asserting it in the prose below.
  const [directWriteTarget, setDirectWriteTarget] = useState<
    "user-data" | "user-accounts" | null
  >(null)
  const [directWriteStatus, setDirectWriteStatus] =
    useState<StepStatus>("pending")
  const [directWriteError, setDirectWriteError] = useState<string | null>(null)
  const [directWriteResult, setDirectWriteResult] = useState<unknown>(null)

  // Website, step 1: create + publish the pairing request — once the reader
  // clicks "start the simulation" below, not on mount. `rendezvous` isn't in
  // the deps array on purpose: its value is stable (module-level defaults or
  // fixed `customFields`), only its object identity changes each render, and
  // this must still run exactly once per `started` transition.
  useEffect(() => {
    if (!started) return
    let cancelled = false
    void (async () => {
      setWebsiteStatus("running")
      try {
        const s = await startPairingRequest({
          origin: window.location.origin,
          label: "Demo Trading Dashboard",
          rendezvous,
          requestedCollections: ["accounts", "userData"],
        })
        await s.publish()
        if (cancelled) return
        setSession(s)
        setWebsiteStatus("done")
      } catch (err) {
        if (cancelled) return
        setWebsiteError(err instanceof Error ? err.message : String(err))
        setWebsiteStatus("error")
      }
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [started])

  // Website, step 3 (starts as soon as the request is published): wait for
  // the phone's grant without polling manually. Resolves once the phone
  // step below mints and publishes.
  useEffect(() => {
    if (!session) return
    let cancelled = false
    setResolveStatus("running")
    // session already carries the rendezvous it was published to.
    awaitPairingGrant(session, { timeoutMs: 5 * 60_000 })
      .then((r) => {
        if (cancelled) return
        setResult(r)
        setResolveStatus("done")
      })
      .catch((err) => {
        if (cancelled) return
        setResolveError(err instanceof Error ? err.message : String(err))
        setResolveStatus("error")
      })
    return () => {
      cancelled = true
    }
  }, [session])

  // Phone, step 2: triggered by the "look up code" button — find the
  // request and show its origin/label so the user has something real to
  // approve or reject. Publishes nothing, creates nothing yet.
  const runPhoneLookup = async () => {
    if (!session) return
    setLookupStatus("running")
    try {
      const found = await fetchPairingRequestByCode({
        code: session.code,
        rendezvous,
      })
      if (!found) throw new Error("no pairing request found for this code")
      setFoundRequest(found.request)
      setFoundRequestHash(found.hash)
      setLookupStatus("done")
    } catch (err) {
      setLookupError(err instanceof Error ? err.message : String(err))
      setLookupStatus("error")
    }
  }

  // Phone, step 3: only reachable once a request was found AND a private
  // key has been entered — the explicit "approve & share" the user clicks
  // after reading the origin/label above. This is the step that actually
  // creates state on the real sync server: a real Starfish space
  // (`octobot-mirror`) owned by whatever identity `phoneKeyInput` derives
  // to. Nothing here runs until this button is clicked — use the "generate
  // a throwaway key" helper below if you don't want to use a key you'd ever
  // want to reclaim, since there is currently no cleanup path for demo
  // spaces once created.
  const runPhoneApprove = async () => {
    if (!foundRequest || !phoneKeyInput.trim()) return
    setShareStatus("running")
    try {
      const { userId, keys } = await deriveRoot(phoneKeyInput.trim(), "bip44")
      setPhoneUserId(userId)
      setPhoneRootEdPub(keys.edPub)

      const newPhoneSession: Session = await buildSession({
        userId,
        keys,
        clientOpts: spacesClientOpts,
        autoProfile: false,
        config: { layout: DEMO_SPACE_LAYOUT },
      })

      await syncCloudMirror({
        session: newPhoneSession,
        enabledCollectionIds: DEMO_ENABLED_COLLECTIONS,
        readSourceCollection: buildReadDemoSourceCollection(btcAmount),
      })
      setPhoneSession(newPhoneSession)
      setLastSyncedAmount(btcAmount)

      const grant = await mintPairingGrant(newPhoneSession, foundRequest)
      setMintedGrant(grant)

      await publishPairingGrant({
        request: foundRequest,
        sealer: { edPrivHex: keys.edPriv, edPubHex: keys.edPub },
        grant,
        rendezvous,
        // The request's own hash from the lookup above, not null — this
        // slot already holds the request, so this write claims exactly the
        // request that was read (a compare-and-swap), not a fresh create.
        baseHash: foundRequestHash,
      })
      setShareStatus("done")
    } catch (err) {
      setShareError(err instanceof Error ? err.message : String(err))
      setShareStatus("error")
    }
  }

  // Phone, step 3b (optional, repeatable): re-run syncCloudMirror against the
  // SAME space with the current `btcAmount` — no new grant, no new cap, just
  // a fresh write to the nodes the grant already covers. This is the button
  // that turns "polling again shows whatever the mirror holds right now"
  // from a claim in the prose below into something you can actually watch
  // happen: change the number, click this, then click "pull the mirror
  // again" on the website side and see the new value arrive.
  const runPhoneResync = async () => {
    if (!phoneSession) return
    setResyncStatus("running")
    try {
      await syncCloudMirror({
        session: phoneSession,
        enabledCollectionIds: DEMO_ENABLED_COLLECTIONS,
        readSourceCollection: buildReadDemoSourceCollection(btcAmount),
      })
      setLastSyncedAmount(btcAmount)
      setResyncStatus("done")
    } catch (err) {
      setResyncError(err instanceof Error ? err.message : String(err))
      setResyncStatus("error")
    }
  }

  // Website, step 4b (optional, repeatable): the SAME live read
  // `awaitPairingGrant` did once, called again by hand. No new session, no
  // new lookup — the grant/cap from step 4 is still valid and still covers
  // the same nodes; this just re-pulls and re-decrypts their current
  // content. `expectedSealer` pins it to the identity that already sealed
  // this grant, same guard `awaitPairingGrant` applied the first time.
  const runWebsiteRefresh = async () => {
    if (!session || !result) return
    setRefreshStatus("running")
    try {
      const refreshed = await fetchPairingGrant(session, { expectedSealer: result.sealedBy })
      if (!refreshed) throw new Error("nothing published at this slot anymore")
      setResult(refreshed)
      setRefreshedAt(new Date().toLocaleTimeString())
      setRefreshStatus("done")
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : String(err))
      setRefreshStatus("error")
    }
  }

  // Website, step 5: try to create a brand-new node directly in the paired
  // mirror space, using nothing but the grant already in hand — no session,
  // no phone involved. Expected outcome: the server rejects it, because the
  // cap's ops are read-only. Proving that is the entire point of this
  // button — a paired website cannot unilaterally write; a change has to be
  // requested, approved, and sent by the user's own device.
  const runWebsiteDirectWrite = async (
    target: "user-data" | "user-accounts",
  ) => {
    if (!session || !result) return
    setDirectWriteTarget(target)
    setDirectWriteStatus("running")
    setDirectWriteError(null)
    setDirectWriteResult(null)
    try {
      const doc =
        target === "user-data"
          ? buildDemoAutomationsDoc(btcAmount)
          : buildDemoAccountsDoc(btcAmount)
      const pushResult = await attemptDirectMirrorWrite({
        rendezvous,
        spaceId: result.spaceId,
        cap: result.cap,
        devEdPrivHex: session.device.edPriv,
        collectionId: target,
        nodeId: crypto.randomUUID(),
        doc,
      })
      // Reaching here would mean the cap was NOT read-only — surfaced as an
      // error state on purpose, since that's the actually-unexpected outcome.
      setDirectWriteResult(pushResult)
      setDirectWriteError(
        "unexpected: the write succeeded — this grant should have been read-only",
      )
      setDirectWriteStatus("error")
    } catch (err) {
      setDirectWriteError(err instanceof Error ? err.message : String(err))
      setDirectWriteStatus("done")
    }
  }

  return (
    <Section
      id="website-pairing"
      eyebrow="device-code pairing · real rendezvous, live sync server"
      title="A website and a phone, paired in one tab"
      weight="normal"
    >
      {!started ? (
        <div className="border border-node-required bg-wire-surface p-4">
          <p className="font-mono text-[12px] text-wire-muted">
            This section runs a real, live pairing request against Drakkar's
            production sync server and waits up to 5 minutes for a phone to
            approve it. Nothing happens until you click below.
          </p>
          <button
            type="button"
            onClick={() => setStarted(true)}
            className="mt-3 rounded-none border border-node-required px-3 py-1.5 font-mono text-[12px] text-node-required hover:bg-node-required/10"
          >
            start the simulation
          </button>
        </div>
      ) : (
        <>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="border border-wire-rule bg-wire-surface p-4">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            website
          </p>
          <ol className="space-y-3">
            <StepRow
              n={1}
              label="startPairingRequest + publish"
              status={websiteStatus}
              detail={websiteError ?? undefined}
            />
            <StepRow
              n={4}
              label="awaitPairingGrant (waiting, no manual polling)"
              status={resolveStatus}
              detail={resolveError ?? undefined}
            />
          </ol>
          {session ? (
            <div className="mt-4 border-t border-wire-rule pt-4">
              <p className="font-mono text-[11px] uppercase tracking-wider text-wire-muted">
                code shown to the user
              </p>
              <p className="mt-1 break-all font-mono text-2xl text-live">
                {session.code}
              </p>
            </div>
          ) : null}
        </div>

        <div className="border border-wire-rule bg-wire-surface p-4">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            phone
          </p>
          <ol className="space-y-3">
            <StepRow
              n={2}
              label="fetchPairingRequestByCode (lookup only — nothing shared yet)"
              status={lookupStatus}
              detail={lookupError ?? undefined}
            />
            <StepRow
              n={3}
              label="mint + publish grant (only after approval, creates a real space)"
              status={shareStatus}
              detail={shareError ?? undefined}
            />
          </ol>
          <button
            type="button"
            onClick={() => void runPhoneLookup()}
            disabled={
              !session || lookupStatus === "running" || lookupStatus === "done"
            }
            className="mt-4 rounded-none border border-live px-3 py-1.5 font-mono text-[12px] text-live hover:bg-live/10 disabled:cursor-not-allowed disabled:border-wire-rule disabled:text-wire-muted disabled:hover:bg-transparent"
          >
            simulate: user typed the code on their phone
          </button>
          {foundRequest ? (
            <div className="mt-4 border-t border-wire-rule pt-4 font-mono text-[12px]">
              <p className="text-wire-muted">
                a website wants to pair —{" "}
                <span className="text-wire-ink">{foundRequest.origin}</span>
              </p>
              {foundRequest.label ? (
                <p className="mt-1 text-wire-muted">
                  label:{" "}
                  <span className="text-wire-ink">{foundRequest.label}</span>
                </p>
              ) : null}
              <p className="mt-1 text-wire-muted">
                requested collections:{" "}
                <span className="text-wire-ink">
                  {(foundRequest.requestedCollections ?? []).join(", ") ||
                    "(none)"}
                </span>
              </p>

              <div className="mt-3 border-t border-wire-rule pt-3">
                <p className="text-wire-muted">
                  phone's private key — approving mints a REAL Starfish space
                  owned by this identity on the live sync server. There is no
                  cleanup path yet, so use a throwaway key unless you want to
                  keep managing this space afterward.
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <input
                    type="text"
                    value={phoneKeyInput}
                    onChange={(e) => setPhoneKeyInput(e.target.value)}
                    placeholder="0x… private key"
                    disabled={
                      shareStatus === "running" || shareStatus === "done"
                    }
                    className="min-w-0 flex-1 border border-wire-rule bg-wire-bg px-2 py-1.5 font-mono text-[12px] text-wire-ink placeholder:text-wire-muted disabled:opacity-60"
                  />
                  <button
                    type="button"
                    onClick={() => setPhoneKeyInput(generateRandomPrivateKey())}
                    disabled={
                      shareStatus === "running" || shareStatus === "done"
                    }
                    className="rounded-none border border-wire-rule px-3 py-1.5 font-mono text-[12px] text-wire-muted hover:text-wire-ink disabled:cursor-not-allowed"
                  >
                    generate throwaway key
                  </button>
                </div>
              </div>

              <button
                type="button"
                onClick={() => void runPhoneApprove()}
                disabled={
                  !phoneKeyInput.trim() ||
                  shareStatus === "running" ||
                  shareStatus === "done"
                }
                className="mt-3 rounded-none border border-live px-3 py-1.5 font-mono text-[12px] text-live hover:bg-live/10 disabled:cursor-not-allowed disabled:border-wire-rule disabled:text-wire-muted disabled:hover:bg-transparent"
              >
                approve &amp; share
              </button>
            </div>
          ) : null}
          {phoneRootEdPub ? (
            <div className="mt-3 font-mono text-[12px]">
              <p className="text-wire-muted">
                phone's own root identity (sealer) — userId{" "}
                <span className="text-wire-ink">{phoneUserId}</span>
              </p>
              <p className="break-all text-wire-muted">
                edPub: <span className="text-wire-ink">{phoneRootEdPub}</span>
              </p>
              {mintedGrant ? (
                <p className="mt-1 break-all text-wire-muted">
                  mirror space:{" "}
                  <span className="text-wire-ink">{mintedGrant.spaceId}</span> ·
                  covers{" "}
                  <span className="text-wire-ink">
                    {mintedGrant.coveredCollections.join(", ")}
                  </span>
                </p>
              ) : null}
            </div>
          ) : null}

          {phoneSession ? (
            <div className="mt-4 border-t border-wire-rule pt-4">
              <p className="font-mono text-[11px] uppercase tracking-wider text-wire-muted">
                sync mirror data again — same space, no new grant
              </p>
              <p className="mt-1 font-mono text-[12px] text-wire-muted">
                change the BTC amount and re-sync — the website panel's "pull
                the mirror again" then shows this exact number, proving the read
                is live rather than a one-time export.
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={btcAmount}
                  onChange={(e) =>
                    setBtcAmount(
                      e.target.value === "" ? 0 : Number(e.target.value),
                    )
                  }
                  disabled={resyncStatus === "running"}
                  className="w-28 border border-wire-rule bg-wire-bg px-2 py-1.5 font-mono text-[12px] text-wire-ink disabled:opacity-60"
                />
                <span className="font-mono text-[12px] text-wire-muted">
                  BTC held by the demo account
                </span>
                <button
                  type="button"
                  onClick={() => void runPhoneResync()}
                  disabled={resyncStatus === "running"}
                  className="rounded-none border border-live px-3 py-1.5 font-mono text-[12px] text-live hover:bg-live/10 disabled:cursor-not-allowed disabled:border-wire-rule disabled:text-wire-muted disabled:hover:bg-transparent"
                >
                  {resyncStatus === "running" ? "syncing…" : "re-sync mirror"}
                </button>
              </div>
              {resyncError ? (
                <p className="mt-2 font-mono text-[11px] text-danger">
                  {resyncError}
                </p>
              ) : null}
              {lastSyncedAmount !== null ? (
                <p className="mt-2 font-mono text-[11px] text-wire-muted">
                  last written to the mirror:{" "}
                  <span className="text-wire-ink">{lastSyncedAmount}</span> BTC
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {result ? (
        <div className="mt-6 border border-wire-rule bg-wire-surface p-4">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            website receives — a live, cap-authenticated read of the mirror
          </p>
          <p className="font-mono text-[12px] text-live">
            grant arrived, sealed by {result.sealedBy}
          </p>
          <p className="mt-2 font-mono text-[12px] text-wire-muted">
            this is a live feed, not a point-in-time export — polling again
            (e.g. <code className="font-mono">fetchPairingGrant</code>) shows
            whatever the mirror holds right now
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void runWebsiteRefresh()}
              disabled={refreshStatus === "running"}
              className="rounded-none border border-live px-3 py-1.5 font-mono text-[12px] text-live hover:bg-live/10 disabled:cursor-not-allowed disabled:border-wire-rule disabled:text-wire-muted disabled:hover:bg-transparent"
            >
              {refreshStatus === "running"
                ? "pulling…"
                : "pull the mirror again"}
            </button>
            {refreshedAt ? (
              <span className="font-mono text-[11px] text-wire-muted">
                pulled at {refreshedAt}
              </span>
            ) : null}
          </div>
          {refreshError ? (
            <p className="mt-2 font-mono text-[11px] text-danger">
              {refreshError}
            </p>
          ) : null}
          <div className="mt-3 grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-1 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
                user-accounts
              </p>
              <pre className="overflow-x-auto rounded-none border border-wire-rule bg-wire-bg p-3 font-mono text-[12px] text-wire-ink">
                {JSON.stringify(result.collections["user-accounts"], null, 2)}
              </pre>
            </div>
            <div>
              <p className="mb-1 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
                user-data (automations)
              </p>
              <pre className="overflow-x-auto rounded-none border border-wire-rule bg-wire-bg p-3 font-mono text-[12px] text-wire-ink">
                {JSON.stringify(result.collections["user-data"], null, 2)}
              </pre>
            </div>
          </div>
          <p className="mt-3 font-mono text-[12px] text-danger">
            note what's absent: no node credential, no private key — the website
            only ever received a `space:member` cap it uses to decrypt the
            mirror's own content, nothing more.
          </p>

          <div className="mt-6 border-t border-wire-rule pt-4">
            <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
              try it anyway — write directly with this grant
            </p>
            <p className="font-mono text-[12px] text-wire-muted">
              the cap above is read-only. Click either button to make the
              website attempt a raw write straight into the node, no phone
              involved — the rejection below is the expected, correct outcome.
              To actually change something, the request has to be approved and
              sent by the user&apos;s own device.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => void runWebsiteDirectWrite("user-data")}
                disabled={directWriteStatus === "running"}
                className="rounded-none border border-danger px-3 py-1.5 font-mono text-[12px] text-danger hover:bg-danger/10 disabled:cursor-not-allowed disabled:border-wire-rule disabled:text-wire-muted disabled:hover:bg-transparent"
              >
                {directWriteStatus === "running" &&
                directWriteTarget === "user-data"
                  ? "writing…"
                  : "try: write a new automation directly"}
              </button>
              <button
                type="button"
                onClick={() => void runWebsiteDirectWrite("user-accounts")}
                disabled={directWriteStatus === "running"}
                className="rounded-none border border-danger px-3 py-1.5 font-mono text-[12px] text-danger hover:bg-danger/10 disabled:cursor-not-allowed disabled:border-wire-rule disabled:text-wire-muted disabled:hover:bg-transparent"
              >
                {directWriteStatus === "running" &&
                directWriteTarget === "user-accounts"
                  ? "writing…"
                  : "try: write a new account directly"}
              </button>
            </div>
            {directWriteStatus !== "pending" && directWriteTarget ? (
              <div className="mt-3 font-mono text-[12px]">
                <p
                  className={
                    directWriteStatus === "done"
                      ? "text-live"
                      : directWriteStatus === "error"
                        ? "text-danger"
                        : "text-wire-muted"
                  }
                >
                  {directWriteStatus === "running"
                    ? "writing…"
                    : directWriteStatus === "done"
                      ? "rejected, as expected — a read-only cap cannot write"
                      : "unexpected — see below"}
                </p>
                {directWriteError ? (
                  <pre className="mt-2 overflow-x-auto rounded-none border border-wire-rule bg-wire-bg p-3 text-[11px] text-wire-ink">
                    {directWriteError}
                  </pre>
                ) : null}
                {directWriteResult ? (
                  <pre className="mt-2 overflow-x-auto rounded-none border border-wire-rule bg-wire-bg p-3 text-[11px] text-wire-ink">
                    {JSON.stringify(directWriteResult, null, 2)}
                  </pre>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
        </>
      )}

      <div className="mt-8 space-y-3 border-t border-wire-rule pt-6 text-[13px] leading-relaxed text-wire-muted">
        <p>
          What's real above: everything, once you click through both phone
          buttons. The pairing request's proof-of-possession signature, the
          phone's wallet derivation (from whatever private key you typed or
          generated), a real Starfish space (
          <code className="font-mono text-wire-ink">octobot-mirror</code>)
          created and written to under that identity, the space-member cap{" "}
          <code className="font-mono text-wire-ink">mintPairingGrant</code>{" "}
          mints and seals to the website's ephemeral KEM key, the website's
          signature-verified unsealing of it, and the rendezvous both sides
          publish to and pull from — the live, public{" "}
          <code className="font-mono text-wire-ink">joinsessions</code>{" "}
          collection on Drakkar's shared sync server (the same address, one
          code-keyed slot, that carries the request and is then overwritten
          in place by the grant). Nothing here talks to an in-memory
          stand-in.
        </p>
        <p>
          What's still fixtures: the phone's portfolio. There's no real OctoBot
          node behind this "phone" — its account and automation data (
          <code className="font-mono text-wire-ink">DEMO_ACCOUNTS_DOC</code>/
          <code className="font-mono text-wire-ink">DEMO_AUTOMATIONS_DOC</code>{" "}
          above) is hardcoded, so the mirror node the website reads is genuinely
          written, encrypted, and decrypted — it just isn't mirroring data
          pulled from anywhere real. The space itself, unlike the fixture data
          inside it, is real and persists after you leave this page.
        </p>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            website side
          </p>
          <CodeBlock language="ts" code={WEBSITE_SNIPPET} />
        </div>
        <div>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            phone side
          </p>
          <CodeBlock language="ts" code={PHONE_SNIPPET} />
        </div>
      </div>
    </Section>
  )
}
