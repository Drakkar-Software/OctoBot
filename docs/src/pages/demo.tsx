import Layout from "@theme/Layout"
import BrowserOnly from "@docusaurus/BrowserOnly"
import "../css/demo.css"

// Content order follows what a skeptical engineer needs to see, in order —
// not the order that leads with the flashiest idea: what it is and what it
// costs, then live crypto with a 0-request counter proving it's local, then
// a real node round-trip, then the failure modes, then the read-only
// pairing flow, then the full website-pairing simulation, then reference.
const NAV = [
  { id: "overview", label: "overview" },
  { id: "derive", label: "derive" },
  { id: "queue", label: "queue" },
  { id: "errors", label: "errors" },
  { id: "propose", label: "propose" },
  { id: "website-pairing", label: "website pairing" },
  { id: "escape-hatches", label: "reference" },
] as const

function DemoApp() {
  const {
    Overview,
  } = require("../components/demo/sections/Overview")
  const {
    DerivationHero,
  } = require("../components/demo/sections/DerivationHero")
  const {
    QueuePanel,
  } = require("../components/demo/sections/QueuePanel")
  const {
    ErrorTaxonomy,
  } = require("../components/demo/sections/ErrorTaxonomy")
  const {
    ProposePanel,
  } = require("../components/demo/sections/ProposePanel")
  const {
    WebsitePairingSim,
  } = require("../components/demo/sections/WebsitePairingSim")
  const {
    EscapeHatches,
  } = require("../components/demo/sections/EscapeHatches")
  const {
    WalletKeyProvider,
  } = require("../components/demo/lib/walletKeyContext")
  const {
    NodeUrlProvider,
  } = require("../components/demo/lib/nodeUrlContext")
  const {
    SecureContextWarning,
  } = require("../components/demo/components/SecureContextWarning")

  return (
    <div className="octobot-demo min-h-screen bg-wire-bg">
      <header className="sticky top-0 z-10 border-b border-wire-rule bg-wire-bg/95 backdrop-blur">
        <nav className="mx-auto flex max-w-5xl items-center gap-5 overflow-x-auto px-6 py-3 md:px-10">
          <span className="whitespace-nowrap font-mono text-[12px] text-wire-ink">
            octobot-client
          </span>
          <div className="flex gap-4">
            {NAV.map((n) => (
              <a
                key={n.id}
                href={`#${n.id}`}
                className="whitespace-nowrap font-mono text-[11px] text-wire-muted transition-colors hover:text-live"
              >
                {n.label}
              </a>
            ))}
          </div>
        </nav>
      </header>

      <main className="px-6 md:px-10">
        <SecureContextWarning />
        <Overview />
        <WalletKeyProvider>
          <NodeUrlProvider>
            <DerivationHero />
            <QueuePanel />
            <ErrorTaxonomy />
            <ProposePanel />
          </NodeUrlProvider>
        </WalletKeyProvider>
        <WebsitePairingSim />
        <EscapeHatches />
      </main>

      <footer className="border-t border-wire-rule px-6 py-8 md:px-10">
        <p className="mx-auto max-w-5xl font-mono text-[11px] text-wire-muted">
          A running reference for @drakkar.software/octobot-client — not
          affiliated with any node you point it at.
        </p>
      </footer>
    </div>
  )
}

export default function DemoPage() {
  return (
    <Layout
      title="Client SDK demo"
      description="A live, in-browser reference for @drakkar.software/octobot-client"
    >
      <BrowserOnly>{() => <DemoApp />}</BrowserOnly>
    </Layout>
  )
}
