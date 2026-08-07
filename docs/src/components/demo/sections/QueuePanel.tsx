import {
  type AccountView,
  type ActionHandle,
  type AutomationView,
  connectOctoBot,
  isOctoBotError,
  type OctoBotClient,
  strategy,
} from "@drakkar.software/octobot-client"
import { useCallback, useEffect, useRef, useState } from "react"
import { CodeBlock } from "../components/CodeBlock"
import { NodeBadge } from "../components/NodeBadge"
import { Section } from "../components/Section"
import { useNodeUrl } from "../lib/nodeUrlContext"
import {
  isExpectedPlaceholderRejection,
  PLACEHOLDER_ACCOUNT_ID,
  usedGenuinePlaceholder,
} from "../lib/placeholderAccount"
import { useWalletKey } from "../lib/walletKeyContext"

type ProgressEvent = { phase: "strategy" | "automation"; done: boolean }

type ThrownError = { message: string; code?: string }

function describeError(err: unknown): ThrownError {
  if (isOctoBotError(err)) return { message: err.message, code: err.code }
  if (err instanceof Error) return { message: err.message }
  return { message: String(err) }
}

// A connection-shaped failure (never reached the node at all) vs. one where
// the node answered but rejected the call — only the former means "not
// reachable". `unreachable`/`timeout`/`aborted` are OctoBotConnectionError;
// everything else (unauthorized, http, action_failed, …) got a real response.
function isConnectionShaped(code: string | undefined): boolean {
  return code === "unreachable" || code === "timeout" || code === "aborted"
}

const CREATE_CODE = `const action = await octobot.automations.create(
  {
    name: 'Demo DCA',
    strategy: strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '10' }),
    accountIds, // ['demo-account'] if no real account exists yet
  },
  {
    onProgress: (p) => console.log(p.phase, p.done), // 'strategy' then 'automation'
  },
)

console.log(action.ids) // already appended — the node has this queued right now

const automation = await action.settled() // polls until both phases confirm
console.log(automation?.id, automation?.status)`

export function QueuePanel() {
  const { privateKey } = useWalletKey()
  const { url, setUrl } = useNodeUrl()
  const [client, setClient] = useState<OctoBotClient | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [connectError, setConnectError] = useState<ThrownError | null>(null)

  const [accounts, setAccounts] = useState<AccountView[] | null>(null)
  const [listing, setListing] = useState(false)
  const [listReachable, setListReachable] = useState<boolean | undefined>(
    undefined,
  )
  const [listError, setListError] = useState<ThrownError | null>(null)

  const [creating, setCreating] = useState(false)
  const [handleIds, setHandleIds] = useState<readonly string[] | null>(null)
  const [progressLog, setProgressLog] = useState<ProgressEvent[]>([])
  const [automation, setAutomation] = useState<AutomationView | null>(null)
  const [createReachable, setCreateReachable] = useState<boolean | undefined>(
    undefined,
  )
  const [createError, setCreateError] = useState<ThrownError | null>(null)
  const [usedPlaceholderAccount, setUsedPlaceholderAccount] = useState(false)

  const onConnect = useCallback(async () => {
    if (!url.trim() || !privateKey) return
    setConnecting(true)
    setConnectError(null)
    try {
      const c = await connectOctoBot({
        url: url.trim(),
        seed: privateKey,
      })
      setClient(c)
    } catch (err) {
      setConnectError(describeError(err))
    } finally {
      setConnecting(false)
    }
  }, [url, privateKey])

  // Auto-connect once a persisted url makes this button clickable on its
  // own — a url only ever reaches localStorage by way of a real connect
  // attempt, so restoring it warrants immediately retrying, not making the
  // user click "connect" again for a value they already entered last time.
  // Guarded by a ref, not an empty dep array: the deps below are honestly
  // exhaustive (nothing for an autofixer to "fix" into re-triggering on
  // every keystroke) — the ref is what makes this fire once.
  const autoConnectAttempted = useRef(false)
  useEffect(() => {
    if (autoConnectAttempted.current) return
    if (client || connecting || !url.trim() || !privateKey) return
    autoConnectAttempted.current = true
    void onConnect()
  }, [client, connecting, url, privateKey, onConnect])

  const onListAccounts = async () => {
    if (!client) return
    setListing(true)
    setListError(null)
    try {
      const list = await client.accounts.list()
      setAccounts(list)
      setListReachable(true)
    } catch (err) {
      const e = describeError(err)
      setListError(e)
      setListReachable(isConnectionShaped(e.code) ? false : undefined)
    } finally {
      setListing(false)
    }
  }

  const onCreateAutomation = async () => {
    if (!client) return
    setCreating(true)
    setHandleIds(null)
    setProgressLog([])
    setAutomation(null)
    setCreateError(null)
    setCreateReachable(undefined)

    const accountIds =
      accounts && accounts.length > 0
        ? [accounts[0].id]
        : [PLACEHOLDER_ACCOUNT_ID]
    setUsedPlaceholderAccount(
      usedGenuinePlaceholder({
        accountId: accountIds[0],
        listSucceeded: listReachable === true && listError === null,
      }),
    )

    try {
      const action: ActionHandle<AutomationView | null> =
        await client.automations.create(
          {
            name: "Demo DCA",
            strategy: strategy.dca({
              pairs: ["BTC/USDT"],
              buyOrderAmount: "10",
            }),
            accountIds,
          },
          {
            onProgress: (p) => setProgressLog((prev) => [...prev, p]),
          },
        )

      // The instant this line runs, the append already happened — settled()
      // below is only about observing the outcome, not causing it.
      setHandleIds(action.ids)

      const result = await action.settled()
      setAutomation(result)
      setCreateReachable(true)
    } catch (err) {
      const e = describeError(err)
      setCreateError(e)
      setCreateReachable(isConnectionShaped(e.code) ? false : undefined)
    } finally {
      setCreating(false)
    }
  }

  return (
    <Section
      id="queue"
      eyebrow="writes are a queue, not an RPC call"
      title="create() returns the moment it's appended, not the moment it's done"
      weight="normal"
    >
      <p className="mb-8 max-w-2xl text-[15px] leading-relaxed text-wire-muted">
        <code className="font-mono text-wire-ink">accounts.create()</code> and{" "}
        <code className="font-mono text-wire-ink">automations.create()</code>{" "}
        don't make an RPC call that finishes when the promise resolves. They
        append an action to the node's queue and hand back an{" "}
        <code className="font-mono text-wire-ink">ActionHandle</code> the
        instant that append happens.{" "}
        <code className="font-mono text-wire-ink">settled()</code> only lets you
        watch what the node does with it afterward. A caller who reads the
        resolved promise as "it's created now" is already wrong — and a caller
        who never calls{" "}
        <code className="font-mono text-wire-ink">settled()</code> at all hasn't
        left anything half-done, the append still happened without them
        watching.
      </p>

      <div className="mb-8">
        <CodeBlock language="ts" code={CREATE_CODE} />
      </div>

      <div className="mb-6 border border-wire-rule bg-wire-surface p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            1 · connect
          </span>
        </div>
        {!client ? (
          <>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="http://localhost:5001"
                className="flex-1 rounded-none border border-wire-rule bg-wire-bg px-3 py-2 font-mono text-[13px] text-wire-ink placeholder:text-wire-muted/60 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => void onConnect()}
                disabled={connecting || !url.trim() || !privateKey}
                className="rounded-none border border-live px-3 py-2 font-mono text-[12px] text-live hover:bg-live/10 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {connecting ? "connecting…" : "connect"}
              </button>
            </div>
            <p className="mt-2 font-mono text-[11px] text-wire-muted">
              the same wallet from the derivation panel above:{" "}
              <span className="break-all text-wire-ink">{privateKey}</span>
            </p>
            <p className="mt-1 font-mono text-[11px] text-wire-muted">
              connect makes one real call here — a probe pull that confirms this
              key is actually authorized on this node — before handing back a
              client. Fails loudly, naming the derived address, rather than
              deferring the problem to the first real read below.
            </p>
            {connectError ? (
              <p className="mt-3 border border-danger/40 bg-danger/[0.06] px-3 py-2 font-mono text-[12px] text-danger">
                {connectError.code ? `[${connectError.code}] ` : ""}
                {connectError.message}
              </p>
            ) : null}
          </>
        ) : (
          <div className="space-y-1 font-mono text-[12px]">
            <p>
              <span className="text-wire-muted">url → </span>
              <span className="text-wire-ink">{client.url}</span>
            </p>
            <p>
              <span className="text-wire-muted">address → </span>
              <span className="break-all text-live">{client.address}</span>
            </p>
            <p>
              <span className="text-wire-muted">userId → </span>
              <span className="break-all text-live">{client.userId}</span>
            </p>
            <p className="pt-1 text-wire-muted">
              resolved locally, zero network calls — not proof anything is
              listening at that url. Step 2 proves that.
            </p>
          </div>
        )}
      </div>

      <div className="mb-6 border border-wire-rule bg-wire-surface p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            2 · read
          </span>
          <NodeBadge reachable={listReachable} />
        </div>
        <button
          type="button"
          onClick={() => void onListAccounts()}
          disabled={!client || listing}
          className="rounded-none border border-wire-rule px-3 py-2 font-mono text-[12px] text-wire-ink hover:border-live hover:text-live disabled:cursor-not-allowed disabled:opacity-40"
        >
          {listing ? "listing…" : "list accounts"}
        </button>

        {listError ? (
          <p className="mt-3 border border-danger/40 bg-danger/[0.06] px-3 py-2 font-mono text-[12px] text-danger">
            {listError.code ? `[${listError.code}] ` : ""}
            {listError.message}
          </p>
        ) : null}

        {accounts && !listError ? (
          accounts.length === 0 ? (
            <p className="mt-3 font-mono text-[12px] text-wire-muted">
              call succeeded — this node really has zero accounts.
            </p>
          ) : (
            <ul className="mt-3 space-y-1 font-mono text-[12px]">
              {accounts.map((a) => (
                <li
                  key={a.id}
                  className="border-b border-wire-rule py-1 last:border-b-0"
                >
                  <span className="text-live">{a.id}</span>
                  <span className="text-wire-muted">
                    {" "}
                    — {a.name} ({a.type})
                  </span>
                </li>
              ))}
            </ul>
          )
        ) : null}
      </div>

      <div className="border border-wire-rule bg-wire-surface p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            3 · write, as a queue
          </span>
          <NodeBadge reachable={createReachable} />
        </div>

        <button
          type="button"
          onClick={() => void onCreateAutomation()}
          disabled={!client || creating}
          className="rounded-none border border-live px-3 py-2 font-mono text-[12px] text-live hover:bg-live/10 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {creating ? "appending…" : "create demo automation"}
        </button>

        {client && !(accounts && accounts.length > 0) ? (
          <p className="mt-2 font-mono text-[11px] text-node-required">
            no real account found yet — will use the placeholder accountId{" "}
            <code className="text-node-required">"demo-account"</code>, which
            does not exist on any node.
          </p>
        ) : null}

        {handleIds ? (
          <div className="mt-4 border-t border-wire-rule pt-3">
            <p className="font-mono text-[11px] uppercase tracking-wider text-wire-muted">
              action.ids — the instant the promise resolved
            </p>
            <p className="mt-1 break-all font-mono text-[13px] text-live">
              {handleIds.length > 0
                ? handleIds.join(", ")
                : "(empty so far — grows as each phase starts)"}
            </p>
            <p className="mt-1 font-mono text-[11px] text-wire-muted">
              already appended — the node has this queued right now, whether or
              not you ever call settled().
            </p>
          </div>
        ) : null}

        {progressLog.length > 0 ? (
          <div className="mt-4 border-t border-wire-rule pt-3">
            <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
              onProgress — strategy_create confirmed before automation_create is
              even sent
            </p>
            <ol className="space-y-1 font-mono text-[12px]">
              {progressLog.map((p, i) => (
                <li
                  key={i}
                  className={p.done ? "text-live" : "text-wire-muted"}
                >
                  phase: {p.phase} · done: {String(p.done)}
                </li>
              ))}
            </ol>
          </div>
        ) : null}

        {createError ? (
          <div className="mt-4 border-t border-wire-rule pt-3">
            <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
              settled() rejected — the append above still happened
            </p>
            {isExpectedPlaceholderRejection({
              usedPlaceholder: usedPlaceholderAccount,
              errorCode: createError.code,
            }) ? (
              <p className="mb-2 font-mono text-[12px] text-node-required">
                expected: the node validated the queued action and correctly
                rejected the placeholder <code>"demo-account"</code> — it
                doesn't exist. List accounts above to find a real one (or create
                one on your node), then try again.
              </p>
            ) : null}
            <p className="border border-danger/40 bg-danger/[0.06] px-3 py-2 font-mono text-[12px] text-danger">
              {createError.code ? `[${createError.code}] ` : ""}
              {createError.message}
            </p>
          </div>
        ) : null}

        {automation ? (
          <div className="mt-4 border-t border-wire-rule pt-3">
            <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
              settled() resolved
            </p>
            <p className="font-mono text-[12px]">
              <span className="text-wire-muted">id → </span>
              <span className="text-live">{automation.id}</span>
              <span className="text-wire-muted"> · status → </span>
              <span className="text-live">{automation.status}</span>
            </p>
          </div>
        ) : null}
      </div>
    </Section>
  )
}
