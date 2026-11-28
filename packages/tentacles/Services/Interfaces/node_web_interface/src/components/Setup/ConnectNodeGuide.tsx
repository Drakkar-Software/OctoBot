import { Globe, Info, Smartphone, TriangleAlert } from "lucide-react"
import { useState } from "react"
import { QRCode } from "react-qr-code"

import { OpenAPI } from "@/client"
import { BrowserAppOpenOrInstallCta } from "@/components/Common/BrowserAppOpenOrInstallCta"
import { ManualNodeConnectPanel } from "@/components/Setup/ManualNodeConnectPanel"
import { NodeConnectAddressTabs } from "@/components/Setup/NodeConnectAddressTabs"
import { SetupPrivateKeyPanel } from "@/components/Setup/SetupPrivateKeyPanel"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { useMobileUi } from "@/hooks/useMobileUi"
import {
  buildMobileUiUrl,
  getMobileUiView,
  isMobileUiOfferable,
} from "@/lib/mobile-ui"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { buildPairingQrValue } from "@/lib/pairing"
import {
  OCTOBOT_CONNECT_GUIDE_COMMON_ISSUES_URL,
  OCTOBOT_CONNECT_GUIDE_URL,
  OCTOBOT_PLAY_STORE_URL,
  OCTOBOT_TESTFLIGHT_URL,
  OCTOBOT_WEB_INTERFACE_URL,
} from "@/lib/external-links"

type ConnectMethod = "web" | "mobile"

const CONNECT_BROWSER_APP_LABEL = "OctoBot browser app (recommended)"
const CONNECT_BROWSER_APP_HELPER =
  "The OctoBot interface served by this node in your browser."
const CONNECT_WEBSITE_LABEL = "Website"
const CONNECT_WEBSITE_HELPER =
  "The hosted OctoBot web app (not this node's browser app)."

const CONNECT_STEP1_OPTION_COLUMN_CLASS =
  "flex h-full flex-col items-start gap-3"

function ConnectWebStep1WebsiteColumn() {
  return (
    <div className={CONNECT_STEP1_OPTION_COLUMN_CLASS}>
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {CONNECT_WEBSITE_LABEL}
      </span>
      <p className="text-sm text-muted-foreground">{CONNECT_WEBSITE_HELPER}</p>
      <div className="mt-auto">
        <Button type="button" variant="outline" size="sm" asChild>
          <a
            href={OCTOBOT_WEB_INTERFACE_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open web interface
          </a>
        </Button>
      </div>
    </div>
  )
}

function ConnectWebStep1OpenInterface() {
  const { user } = useAuth()
  const { status, isLoading } = useMobileUi()
  const isAdmin = user?.is_superuser === true
  const view = getMobileUiView(status, isAdmin)
  const showBrowserAppColumn = isMobileUiOfferable(isLoading, view)
  const openUrl = buildMobileUiUrl(OpenAPI.BASE, window.location.origin)

  return (
    <Card>
      <CardHeader>
        <CardTitle>1. Open an OctoBot interface</CardTitle>
        <CardDescription>
          Choose how you open OctoBot. Prefer Brave or Google Chrome.
        </CardDescription>
      </CardHeader>
      <CardContent
        className={
          showBrowserAppColumn ? "grid gap-4 md:grid-cols-2" : undefined
        }
      >
        {showBrowserAppColumn ? (
          <div
            className={CONNECT_STEP1_OPTION_COLUMN_CLASS}
            aria-busy={isLoading || undefined}
          >
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {CONNECT_BROWSER_APP_LABEL}
            </span>
            <p className="text-sm text-muted-foreground">
              {CONNECT_BROWSER_APP_HELPER}
            </p>
            <div className="mt-auto w-full">
              <BrowserAppOpenOrInstallCta openHref={openUrl} />
            </div>
          </div>
        ) : null}
        <ConnectWebStep1WebsiteColumn />
      </CardContent>
    </Card>
  )
}

export function ConnectNodeGuide() {
  const [connectMethod, setConnectMethod] = useState<ConnectMethod>("web")
  const [showQr, setShowQr] = useState(false)
  const [qrValue, setQrValue] = useState<string | null>(null)
  const [qrError, setQrError] = useState<string | null>(null)

  const selectMethod = (method: ConnectMethod) => {
    setConnectMethod(method)
    setShowQr(false)
    setQrValue(null)
    setQrError(null)
  }

  const switchToWeb = () => {
    selectMethod("web")
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  const revealQr = async () => {
    setQrError(null)
    try {
      setQrValue(await buildPairingQrValue())
    } catch (error) {
      console.error("ConnectNodeGuide: failed to build QR value", error)
      setQrError(error instanceof Error ? error.message : "Failed to build QR code")
      return
    }
    setShowQr(true)
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex rounded-md border text-sm">
        <button
          type="button"
          onClick={() => selectMethod("web")}
          className={`flex flex-1 items-center justify-center gap-2 rounded-l-md px-4 py-2 transition-colors ${
            connectMethod === "web"
              ? "bg-primary text-primary-foreground"
              : "hover:bg-muted"
          }`}
        >
          <Globe className="size-4" />
          Web
        </button>
        <button
          type="button"
          onClick={() => selectMethod("mobile")}
          className={`flex flex-1 items-center justify-center gap-2 rounded-r-md px-4 py-2 transition-colors ${
            connectMethod === "mobile"
              ? "bg-primary text-primary-foreground"
              : "hover:bg-muted"
          }`}
        >
          <Smartphone className="size-4" />
          Mobile
        </button>
      </div>

      {connectMethod === "web" ? (
        <div className="flex flex-col gap-4">
          <ConnectWebStep1OpenInterface />

          <Card>
            <CardHeader>
              <CardTitle>2. Sign in with your wallet</CardTitle>
              <CardDescription>
                Click <strong>I already have a wallet</strong>, then{" "}
                <strong>I already have a private key</strong>.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>3. Copy your private key from this Node</CardTitle>
              <CardDescription>
                Copy the private key below and paste it into the web interface.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SetupPrivateKeyPanel />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>4. Connect this node</CardTitle>
              <div className="flex items-start gap-2 rounded-md border bg-muted/40 p-3 text-sm w-full">
                <Info className="mt-0.5 size-4 shrink-0" />
                <span>
                  Using the <strong>OctoBot browser app</strong>? This step is
                  already done for you. The pairing steps below apply when you
                  use the <strong>website</strong>.
                </span>
              </div>
              <CardDescription>
                In the web interface, start a <strong>new automation</strong>,
                click any kind of automation, then <strong>Add a node</strong> →{" "}
                <strong>Existing install</strong>. Paste this node&apos;s{" "}
                <strong>hostname</strong> and <strong>port</strong> below:
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <NodeConnectAddressTabs audience="web" />
              <p className="pt-2 text-center text-sm text-muted-foreground">
                Having trouble connecting to your node?{" "}
                Try using <strong>Brave</strong> or <strong>Google Chrome</strong> instead of <strong>Firefox</strong> or <strong>Safari</strong>, which are known to sometimes block the
                connection to the node.
              </p>
              <p className="text-center text-sm text-muted-foreground">
                See our{" "}
                <a
                  href={OCTOBOT_CONNECT_GUIDE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-4 hover:text-foreground"
                >
                  full connect guide
                </a>{" "}
                and{" "}
                <a
                  href={OCTOBOT_CONNECT_GUIDE_COMMON_ISSUES_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-4 hover:text-foreground"
                >
                  common issues
                </a>{" "}
                if the web app shows Unreachable node or Queued actions.
              </p>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <div className="flex justify-center pb-2">
                <Smartphone className="size-12 text-primary" />
              </div>
              <CardTitle>1. Download the app</CardTitle>
              <CardDescription>
                Connect to your node, manage your OctoBots, and link your exchange
                accounts.
              </CardDescription>
              <p className="text-sm text-muted-foreground pt-1">
                Available on Android as a beta version (enable beta access for the
                OctoBot app on Google Play) and on iOS as a beta via TestFlight.
              </p>
            </CardHeader>
            <CardContent className="flex flex-row flex-wrap items-center justify-center gap-3">
              <a
                href={OCTOBOT_TESTFLIGHT_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
              >
                App Store
              </a>
              <a
                href={OCTOBOT_PLAY_STORE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
              >
                Google Play
              </a>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>2. Open the app</CardTitle>
              <CardDescription>
                Tap <strong>I already have a wallet</strong>, then{" "}
                <strong>Import from my OctoBot node</strong>.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>3. Scan the QR code</CardTitle>
              <CardDescription>
                Scan the QR code below from the mobile app to connect.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-4">
              {qrError && (
                <p className="text-sm text-destructive text-center">{qrError}</p>
              )}
              {!showQr ? (
                <Button variant="outline" onClick={revealQr}>
                  Show QR code
                </Button>
              ) : (
                <>
                  <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn w-full">
                    <TriangleAlert className="mt-0.5 size-4 shrink-0" />
                    <span>
                      Only scan on a trusted device. The QR code contains your
                      passphrase.
                    </span>
                  </div>
                  {qrValue && (
                    <div className="rounded-xl bg-white p-4">
                      <QRCode value={qrValue} size={180} />
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card className="border-dashed bg-muted/30">
            <CardHeader>
              <CardTitle className="text-muted-foreground">
                4. Add your node manually{" "}
                <span className="text-xs font-normal">(optional)</span>
              </CardTitle>
              <CardDescription>
                If the app did not connect after scanning the QR code, in the
                app start a <strong>new automation</strong>, click any kind of
                automation, then <strong>Add a node</strong> →{" "}
                <strong>Existing install</strong>. Paste this node&apos;s{" "}
                <strong>hostname</strong> and <strong>port</strong> below:
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <ManualNodeConnectPanel onSwitchToWeb={switchToWeb} />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
