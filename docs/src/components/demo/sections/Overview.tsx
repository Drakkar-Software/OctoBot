import { CodeBlock } from "../components/CodeBlock"
import { Section } from "../components/Section"

const NOT_THIS = [
  [
    "No local state",
    "Every read is a fresh pull from the node; nothing is cached.",
  ],
  ["No persistence", "There is no store, no database, no AsyncStorage."],
  [
    "No offline queue",
    "If the node is unreachable, a call fails — it does not queue for later.",
  ],
  [
    "No CRDT merge",
    "No concept of “local edits reconciled with remote state.”",
  ],
  [
    "No React",
    "No hooks, no components, no UI-framework dependency — this demo is one.",
  ],
] as const

export function Overview() {
  return (
    <Section
      id="overview"
      eyebrow="octobot-client · v0.2.0 · GPL-3.0"
      title="What this is, and what it costs you"
      weight="compact"
    >
      <p className="mb-6 text-[15px] leading-relaxed text-wire-muted">
        A TypeScript client for a self-hosted OctoBot trading node: wallet
        identity, accounts, automations, strategies, and an append-only action
        queue, over the Starfish sync transport. No cloud account, no
        registration — anyone running their own node can be your{" "}
        <code className="font-mono text-wire-ink">url</code>.
      </p>

      <ul className="mb-8 grid gap-2 sm:grid-cols-2">
        {NOT_THIS.map(([title, detail]) => (
          <li key={title} className="border border-wire-rule px-3 py-2">
            <p className="font-mono text-[12px] text-wire-ink">{title}</p>
            <p className="mt-0.5 text-[12px] leading-snug text-wire-muted">
              {detail}
            </p>
          </li>
        ))}
      </ul>

      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        <div className="border border-wire-rule px-4 py-3">
          <p className="mb-1 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            runtime requirements
          </p>
          <p className="font-mono text-[12px] leading-relaxed text-wire-ink">
            WebCrypto (crypto.subtle), fetch, btoa/atob, AbortController.
            <br />
            <span className="text-wire-muted">
              Native in Node ≥18, every modern browser, Deno, Bun. React Native
              needs a crypto polyfill this package does not bundle.
            </span>
          </p>
        </div>
        <div className="border border-wire-rule px-4 py-3">
          <p className="mb-1 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
            license
          </p>
          <p className="font-mono text-[12px] text-wire-ink">
            GPL-3.0
            <br />
            <span className="text-wire-muted">
              worth knowing before week three, not after.
            </span>
          </p>
        </div>
      </div>

      <div className="border border-wire-rule bg-wire-surface px-4 py-3">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
          install
        </p>
        <CodeBlock
          language="bash"
          code="npm install @drakkar.software/octobot-client"
        />
      </div>

      <div className="mt-6">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-wire-muted">
          hello world
        </p>
        <CodeBlock
          language="ts"
          code={`import { connectOctoBot, strategy } from '@drakkar.software/octobot-client'

const octobot = await connectOctoBot({
  url: 'http://192.168.1.10:5001',
  seed: process.env.OCTOBOT_PRIVATE_KEY!, // a raw 0x-prefixed private key
})

const [account] = await octobot.accounts.list()
const dca = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
const action = await octobot.automations.create({ name: 'My DCA', strategy: dca, accountIds: [account.id] })
const automation = await action.settled()   // polls the node until it confirms
console.log(automation.id, automation.status)`}
        />
      </div>
    </Section>
  )
}
