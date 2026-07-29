import { Globe, Smartphone, TriangleAlert } from "lucide-react"
import { useState } from "react"
import { QRCode } from "react-qr-code"

import { ManualNodeConnectPanel } from "@/components/Setup/ManualNodeConnectPanel"
import { NodeConnectAddressTabs } from "@/components/Setup/NodeConnectAddressTabs"
import { SetupPrivateKeyPanel } from "@/components/Setup/SetupPrivateKeyPanel"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { buildPairingQrValue } from "@/lib/pairing"
import {
  OCTOBOT_BETA_GETTING_STARTED_GUIDE_URL,
  OCTOBOT_PLAY_STORE_URL,
  OCTOBOT_TESTFLIGHT_URL,
  OCTOBOT_WEB_INTERFACE_URL,
} from "@/lib/external-links"

type ConnectMethod = "web" | "mobile"

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
          <Card>
            <CardHeader>
              <CardTitle>1. Open the OctoBot web interface</CardTitle>
              <CardDescription>
                Connect to your node, manage your OctoBots, and link your exchange
                accounts. To avoid compatibility issues, we recommend using{" "}
                <strong>Brave</strong> or <strong>Google Chrome</strong>.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex justify-center">
              <a
                href={OCTOBOT_WEB_INTERFACE_URL}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button type="button" variant="outline">
                  Open web interface
                </Button>
              </a>
            </CardContent>
          </Card>

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
                connection to the node. More troubleshooting tips on{" "}
                <a
                  href={OCTOBOT_BETA_GETTING_STARTED_GUIDE_URL}
                  target="_blank"
                  rel="noopener"
                  className="underline underline-offset-4 hover:text-foreground"
                >
                  our full guide
                </a>
                .
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
