import BrowserOnly from "@docusaurus/BrowserOnly"
import "../../css/demo.css"

export type DemoSectionId =
  | "overview"
  | "derive"
  | "queue"
  | "errors"
  | "propose"
  | "website-pairing"
  | "escape-hatches"

const NEEDS_WALLET_AND_NODE: ReadonlySet<DemoSectionId> = new Set([
  "derive",
  "queue",
  "propose",
])

// One section per docs page, matched to whatever that page is teaching. Each
// embed gets its OWN WalletKeyProvider/NodeUrlProvider instance — unlike
// /demo (pages/demo.tsx), where all sections share one, so trying a key on
// one page doesn't leak into another's local state. That mirrors how a
// reader actually encounters these: as independent examples, not one
// continuous session.
export function DemoEmbed({ section }: { section: DemoSectionId }) {
  return (
    <BrowserOnly fallback={<div className="octobot-demo" />}>
      {() => {
        // `require()`, not a top-level `import` — Docusaurus prerenders
        // every page with `react-dom/server`, and the SDK / starfish-spaces
        // touch browser-only globals (crypto.subtle, window) in places. This
        // callback only ever runs client-side, so requiring here keeps those
        // modules out of the server bundle's module graph entirely. This is
        // the pattern Docusaurus's own BrowserOnly docs recommend.
        const { Overview } = require("./sections/Overview")
        const { DerivationHero } = require("./sections/DerivationHero")
        const { QueuePanel } = require("./sections/QueuePanel")
        const { ErrorTaxonomy } = require("./sections/ErrorTaxonomy")
        const { ProposePanel } = require("./sections/ProposePanel")
        const { WebsitePairingSim } = require("./sections/WebsitePairingSim")
        const { EscapeHatches } = require("./sections/EscapeHatches")
        const { WalletKeyProvider } = require("./lib/walletKeyContext")
        const { NodeUrlProvider } = require("./lib/nodeUrlContext")
        const {
          SecureContextWarning,
        } = require("./components/SecureContextWarning")

        const Component = {
          overview: Overview,
          derive: DerivationHero,
          queue: QueuePanel,
          errors: ErrorTaxonomy,
          propose: ProposePanel,
          "website-pairing": WebsitePairingSim,
          "escape-hatches": EscapeHatches,
        }[section]

        const body = NEEDS_WALLET_AND_NODE.has(section) ? (
          <WalletKeyProvider>
            <NodeUrlProvider>
              <Component />
            </NodeUrlProvider>
          </WalletKeyProvider>
        ) : (
          <Component />
        )

        return (
          <div className="octobot-demo">
            <SecureContextWarning />
            {body}
          </div>
        )
      }}
    </BrowserOnly>
  )
}

export default DemoEmbed
