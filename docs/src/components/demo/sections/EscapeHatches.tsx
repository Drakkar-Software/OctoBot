import { CodeBlock } from "../components/CodeBlock"
import { Section } from "../components/Section"

const COMPAT = [
  { pkg: "This package", version: "0.2.0" },
  { pkg: "@drakkar.software/octobot-protocol", version: "^0.6.0" },
  { pkg: "Minimum node", version: "protocol 0.4.0" },
] as const

export function EscapeHatches() {
  return (
    <Section
      id="escape-hatches"
      eyebrow="reference · escape hatches"
      title="When the typed API isn't enough"
      weight="compact"
    >
      <p className="mb-8 text-[15px] leading-relaxed text-wire-muted">
        Everything above is the paved path. These five are the ways out of it —
        for proxies, for collections this package hasn't wrapped yet, for
        skipping I/O you don't want, and for knowing which node you can actually
        talk to.
      </p>

      <div className="mb-8 border-b border-wire-rule pb-8">
        <p className="mb-1 font-mono text-[13px] text-wire-ink">Custom fetch</p>
        <p className="mb-3 text-[13px] leading-relaxed text-wire-muted">
          <code className="font-mono text-wire-ink">ConnectOptions.fetch</code>{" "}
          — for proxies, mTLS, or a React Native crypto/fetch polyfill.
        </p>
        <CodeBlock
          language="ts"
          code={`const octobot = await connectOctoBot({ url, seed, fetch: myProxyAwareFetch })`}
        />
      </div>

      <div className="mb-8 border-b border-wire-rule pb-8">
        <p className="mb-1 font-mono text-[13px] text-wire-ink">
          verify: false
        </p>
        <p className="mb-3 text-[13px] leading-relaxed text-wire-muted">
          Skips the connect-time probe.{" "}
          <code className="font-mono text-wire-ink">connectOctoBot()</code> then
          does zero I/O, and the first real call (e.g.{" "}
          <code className="font-mono text-wire-ink">accounts.list()</code>)
          surfaces any connectivity or auth problem lazily instead.
        </p>
        <CodeBlock
          language="ts"
          code={`const octobot = await connectOctoBot({ url, seed, verify: false })`}
        />
      </div>

      <div className="mb-8 border-b border-wire-rule pb-8">
        <p className="mb-1 font-mono text-[13px] text-wire-ink">
          Raw documents — client.documents
        </p>
        <p className="mb-3 text-[13px] leading-relaxed text-wire-muted">
          Escape hatch for any collection this package's typed facades don't
          cover, typed loosely.{" "}
          <code className="font-mono text-wire-ink">client.documents.raw</code>{" "}
          exposes the underlying{" "}
          <code className="font-mono text-wire-ink">StarfishClient</code> and
          cap provider directly for anyone building a lower-level integration.
        </p>
        <CodeBlock
          language="ts"
          code={`type DocumentsApi = {
  pull<T>(collection: string, opts?): Promise<{ data: T; hash: string }>
  push(collection: string, data: unknown, opts: { baseHash: string | null; accountId?: string }): Promise<void>
  append(collection: string, element: unknown, opts?): Promise<void>
  raw: {
    sync: unknown /* StarfishClient */
    capProvider: unknown
    encryptorFor(collection: string): Promise<unknown>
    pullPath: unknown
    pushPath: unknown
  }
}

const { data, hash } = await octobot.documents.pull('settings')`}
        />
      </div>

      <div className="mb-8 border-b border-wire-rule pb-8">
        <p className="mb-1 font-mono text-[13px] text-wire-ink">
          seedDerivation: 'auto'
        </p>
        <p className="mb-3 text-[13px] leading-relaxed text-wire-muted">
          Tries every scheme currently registered in the derivation-scheme
          registry — <code className="font-mono text-wire-ink">bip44</code> is
          the only one this package ships by default — and keeps whichever one
          the node authorizes. It's really only useful once a consumer has
          registered a second scheme via{" "}
          <code className="font-mono text-wire-ink">
            registerDerivationScheme
          </code>{" "}
          (from{" "}
          <code className="font-mono text-wire-ink">
            @drakkar.software/octobot-client/identity
          </code>
          ) for a different wallet type; with only{" "}
          <code className="font-mono text-wire-ink">bip44</code> registered,{" "}
          <code className="font-mono text-wire-ink">'auto'</code> and{" "}
          <code className="font-mono text-wire-ink">'bip44'</code> behave
          identically except{" "}
          <code className="font-mono text-wire-ink">'auto'</code> costs an extra
          round-trip.
        </p>
        <CodeBlock
          language="ts"
          code={`const octobot = await connectOctoBot({ url, seed, seedDerivation: 'auto' })`}
        />
      </div>

      <div>
        <p className="mb-1 font-mono text-[13px] text-wire-ink">
          Compatibility
        </p>
        <p className="mb-3 text-[13px] leading-relaxed text-wire-muted">
          This demo audits every claim in this section against the real source
          rather than trusting the README verbatim — the README's compat table
          is currently stale (it still shows{" "}
          <code className="font-mono text-wire-ink">0.1.x</code>); the numbers
          below are the real ones.
        </p>
        <div className="overflow-x-auto border border-wire-rule">
          <table className="w-full border-collapse text-left font-mono text-[12px]">
            <thead>
              <tr className="border-b border-wire-rule text-wire-muted">
                <th className="px-3 py-2 font-normal uppercase tracking-wider">
                  package
                </th>
                <th className="px-3 py-2 font-normal uppercase tracking-wider">
                  required version
                </th>
              </tr>
            </thead>
            <tbody>
              {COMPAT.map(({ pkg, version }) => (
                <tr
                  key={pkg}
                  className="border-b border-wire-rule last:border-b-0"
                >
                  <td className="px-3 py-2 text-wire-muted">{pkg}</td>
                  <td className="px-3 py-2 text-wire-ink">{version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Section>
  )
}
