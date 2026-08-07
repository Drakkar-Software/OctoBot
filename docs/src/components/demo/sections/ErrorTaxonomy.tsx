import {
  isOctoBotError,
  OctoBotActionError,
  OctoBotAuthError,
  OctoBotConfigError,
  OctoBotConflictError,
  OctoBotConnectionError,
  type OctoBotErrorCode,
  OctoBotHttpError,
  OctoBotScopeError,
  OctoBotTimeoutError,
} from "@drakkar.software/octobot-client"
import { useMemo, useState } from "react"
import { CodeBlock } from "../components/CodeBlock"
import { Section } from "../components/Section"

type Field = { label: string; value: string }

type Entry = {
  key: string
  className: string
  /** null for the one entry that is not an OctoBotError at all. */
  code: OctoBotErrorCode | null
  when: string
  build: () => Error | DOMException
  handlerCode: string
  /** A gotcha worth calling out even though nothing here is "live" data. */
  note?: string
  noteTone?: "muted" | "danger"
}

const ENTRIES: Entry[] = [
  {
    key: "config",
    className: "OctoBotConfigError",
    code: "config",
    when: "Bad ConnectOptions — an unparseable url — or a client.node.* call made without basicAuth.",
    build: () =>
      new OctoBotConfigError(
        'could not parse ConnectOptions.url: "htp:/my-node"',
      ),
    handlerCode: `try {
  await connectOctoBot({ url: 'htp:/my-node', seed })
} catch (err) {
  if (isOctoBotError(err) && err.code === 'config') { /* fix ConnectOptions and retry */ }
}`,
  },
  {
    key: "unreachable",
    className: "OctoBotConnectionError",
    code: "unreachable",
    when: "The node could not be reached at all — offline, wrong port, or the connect-time abort fired.",
    build: () =>
      new OctoBotConnectionError(
        "unreachable",
        "could not reach http://192.168.1.10:5001",
        new TypeError("fetch failed"),
      ),
    handlerCode: `try {
  const octobot = await connectOctoBot({ url, seed })
} catch (err) {
  if (isOctoBotError(err) && err.code === 'unreachable') { /* offer a retry — node looks offline */ }
}`,
    note: "Same class also throws with code 'timeout' (the connect-time budget expired) or 'aborted' (the caller's own AbortSignal fired during connect).",
    noteTone: "muted",
  },
  {
    key: "unauthorized",
    className: "OctoBotAuthError",
    code: "unauthorized",
    when: "The node answered, but did not authorize this wallet.",
    build: () =>
      new OctoBotAuthError(
        "0x1234567890AbcdEF1234567890aBcdef12345678",
        "a3f9c2e1b6d84f07c5e0912ab34fd678",
        "bip44",
      ),
    handlerCode: `try {
  await octobot.accounts.list()
} catch (err) {
  if (isOctoBotError(err) && err.code === 'unauthorized') { /* err.address / err.userId / err.derivation name the mismatch */ }
}`,
  },
  {
    key: "http",
    className: "OctoBotHttpError",
    code: "http",
    when: "A client.node.* REST call answered non-2xx.",
    build: () => new OctoBotHttpError(503),
    handlerCode: `try {
  await octobot.node.dslKeywords()
} catch (err) {
  if (isOctoBotError(err) && err.code === 'http') { /* err.status is the REST status the node answered with */ }
}`,
  },
  {
    key: "conflict",
    className: "OctoBotConflictError",
    code: "conflict",
    when: "A document push raced another writer — the baseHash you pushed against is no longer current.",
    build: () => new OctoBotConflictError(null),
    handlerCode: `try {
  await octobot.documents.push('settings', data, { baseHash })
} catch (err) {
  if (isOctoBotError(err) && err.code === 'conflict') { /* pull again, merge, retry with the new hash */ }
}`,
    note: "serverHash carries the node's current hash — the retry hint — so a caller can pull-and-retry without a round trip. Shown as null here only because this is a synthetic instance, not a live conflict.",
    noteTone: "muted",
  },
  {
    key: "action_failed",
    className: "OctoBotActionError",
    code: "action_failed",
    when: "The node executed a queued action and rejected it. Not retriable by resubmitting unchanged.",
    build: () =>
      new OctoBotActionError(
        "insufficient balance: wallet holds 12.4 USDT, action requires 25 USDT",
        "execute",
      ),
    handlerCode: `try {
  await action.settled()
} catch (err) {
  if (isOctoBotError(err) && err.code === 'action_failed') { /* err.detail / err.phase describe what the node rejected */ }
}`,
  },
  {
    key: "action_timeout",
    className: "OctoBotTimeoutError",
    code: "action_timeout",
    when: "ActionHandle.settled() gave up waiting for the node to confirm.",
    build: () => new OctoBotTimeoutError("confirm"),
    handlerCode: `try {
  await action.settled()
} catch (err) {
  if (isOctoBotError(err) && err.code === 'action_timeout') { /* not necessarily a failure — poll action.status() */ }
}`,
    note: "Not necessarily a failure — the action may still complete on the node; this only means settled() stopped waiting.",
    noteTone: "muted",
  },
  {
    key: "forbidden_collection",
    className: "OctoBotScopeError",
    code: "forbidden_collection",
    when: "A read-only session reached a collection its pairing grant doesn't cover — thrown client-side, before any request.",
    build: () => new OctoBotScopeError("accountTrading"),
    handlerCode: `try {
  await octobot.accounts.list()
} catch (err) {
  if (isOctoBotError(err) && err.code === 'forbidden_collection') { /* err.collection names what's missing — no request was sent */ }
}`,
  },
  {
    key: "abort",
    className: "AbortError (DOMException)",
    code: null,
    when: "A caller's own AbortSignal fired. Let through unwrapped, per platform convention — not one of the classes above.",
    build: () => new DOMException("The operation was aborted.", "AbortError"),
    handlerCode: `try {
  await octobot.automations.create(config, { signal })
} catch (err) {
  if (err instanceof DOMException && err.name === 'AbortError') { /* your own signal fired, not an OctoBotError */ }
  else if (isOctoBotError(err)) { /* ... */ }
}`,
    note: "isOctoBotError(new DOMException('aborted', 'AbortError')) is false — a caller's own abort handling has to check for this separately.",
    noteTone: "danger",
  },
]

function extraFields(instance: Error | DOMException): Field[] {
  if (instance instanceof OctoBotAuthError) {
    return [
      { label: ".address", value: instance.address },
      { label: ".userId", value: instance.userId },
      { label: ".derivation", value: instance.derivation },
    ]
  }
  if (instance instanceof OctoBotHttpError) {
    return [{ label: ".status", value: String(instance.status) }]
  }
  if (instance instanceof OctoBotConflictError) {
    return [
      {
        label: ".serverHash",
        value: instance.serverHash === null ? "null" : instance.serverHash,
      },
    ]
  }
  if (instance instanceof OctoBotActionError) {
    return [
      { label: ".phase", value: instance.phase ?? "undefined" },
      { label: ".detail", value: instance.detail ?? "null" },
    ]
  }
  if (instance instanceof OctoBotTimeoutError) {
    return [{ label: ".phase", value: instance.phase ?? "undefined" }]
  }
  if (instance instanceof OctoBotScopeError) {
    return [{ label: ".collection", value: instance.collection }]
  }
  return []
}

export function ErrorTaxonomy() {
  const [selectedKey, setSelectedKey] = useState(ENTRIES[0].key)
  const selected = ENTRIES.find((e) => e.key === selectedKey) ?? ENTRIES[0]
  const instance = useMemo(() => selected.build(), [selected])
  const extra = extraFields(instance)

  return (
    <Section
      id="errors"
      eyebrow="every way a call can fail"
      title="The error taxonomy"
      weight="normal"
    >
      <p className="mb-6 max-w-2xl text-[15px] leading-relaxed text-wire-muted">
        Nine ways a call into this SDK ends badly — eight typed{" "}
        <code className="font-mono text-wire-ink">OctoBotError</code>{" "}
        subclasses, plus one you have to catch yourself. This whole panel is
        offline: click an entry to construct a real instance of that class right
        here in the tab. Nothing below is a hand-written string — it is the
        actual <code className="font-mono text-wire-ink">.message</code> the
        constructor produced.
      </p>

      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <ul className="space-y-2">
          {ENTRIES.map((entry) => (
            <li key={entry.key}>
              <button
                type="button"
                onClick={() => setSelectedKey(entry.key)}
                aria-pressed={entry.key === selectedKey}
                className={`w-full border px-3 py-2 text-left transition-colors ${
                  entry.key === selectedKey
                    ? "border-wire-ink bg-wire-surface-raised"
                    : "border-wire-rule bg-wire-surface hover:border-wire-muted"
                }`}
              >
                <p className="font-mono text-[13px] text-wire-ink">
                  {entry.className}
                </p>
                <p className="mt-0.5 font-mono text-[11px] text-wire-muted">
                  {entry.code === null
                    ? "not an OctoBotError"
                    : `code: '${entry.code}'`}
                </p>
                <p className="mt-1 text-[12px] leading-snug text-wire-muted">
                  {entry.when}
                </p>
              </button>
            </li>
          ))}
        </ul>

        <div className="space-y-4">
          <div className="border border-wire-rule bg-wire-surface p-4">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
              new {selected.className}(…) — real output
            </p>
            <dl className="space-y-2 font-mono text-[13px]">
              <div className="flex gap-3">
                <dt className="w-28 shrink-0 text-wire-muted">.name</dt>
                <dd className="break-words text-wire-ink">{instance.name}</dd>
              </div>
              {isOctoBotError(instance) ? (
                <div className="flex gap-3">
                  <dt className="w-28 shrink-0 text-wire-muted">.code</dt>
                  <dd className="text-wire-ink">'{instance.code}'</dd>
                </div>
              ) : (
                <div className="flex gap-3">
                  <dt className="w-28 shrink-0 text-wire-muted">
                    isOctoBotError()
                  </dt>
                  <dd className="text-danger">false</dd>
                </div>
              )}
              <div className="flex gap-3">
                <dt className="w-28 shrink-0 text-wire-muted">.message</dt>
                <dd className="break-words text-wire-ink">
                  {instance.message}
                </dd>
              </div>
              {isOctoBotError(instance) && instance.cause !== undefined ? (
                <div className="flex gap-3">
                  <dt className="w-28 shrink-0 text-wire-muted">.cause</dt>
                  <dd className="break-words text-wire-ink">
                    {instance.cause instanceof Error
                      ? instance.cause.message
                      : String(instance.cause)}
                  </dd>
                </div>
              ) : null}
              {extra.map((f) => (
                <div key={f.label} className="flex gap-3">
                  <dt className="w-28 shrink-0 text-wire-muted">{f.label}</dt>
                  <dd className="break-all text-wire-ink">{f.value}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div>
            <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
              handler
            </p>
            <CodeBlock language="ts" code={selected.handlerCode} />
          </div>

          {selected.note ? (
            <p
              className={`text-[12px] leading-relaxed ${selected.noteTone === "danger" ? "text-danger" : "text-wire-muted"}`}
            >
              {selected.note}
            </p>
          ) : null}
        </div>
      </div>
    </Section>
  )
}
