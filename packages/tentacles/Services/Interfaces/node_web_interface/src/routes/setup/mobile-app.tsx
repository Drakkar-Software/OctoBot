import { createFileRoute, Link, redirect, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { Smartphone, TriangleAlert } from "lucide-react"
import QRCode from "react-qr-code"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/setup/mobile-app")({
  beforeLoad: () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/setup" })
    }
  },
  component: SetupMobileApp,
  head: () => ({
    meta: [{ title: "Setup — Mobile App" }],
  }),
})

const APP_STORE_URL =
  "https://apps.apple.com/us/app/octobot-crypto-investment/id6502774175"
const PLAY_STORE_URL =
  "https://play.google.com/store/apps/details?id=com.drakkarsoftware.octobotapp"

function SetupMobileApp() {
  const navigate = useNavigate()
  const [showQr, setShowQr] = useState(false)
  const [qrValue, setQrValue] = useState<string | null>(null)

  const finishSetup = () => {
    sessionStorage.removeItem("setup_in_progress")
    navigate({ to: "/" })
  }

  const revealQr = () => {
    const address = localStorage.getItem("auth_username") || ""
    const passphrase = localStorage.getItem("auth_password") || ""
    setQrValue(
      JSON.stringify({
        url: window.location.origin,
        address,
        passphrase,
      }),
    )
    setShowQr(true)
  }

  return (
    <div className="flex min-h-svh items-center justify-center p-6">
      <div className="flex w-full max-w-2xl flex-col gap-8">
        <div className="flex flex-col items-center gap-2 text-center">
          <p className="text-xs text-muted-foreground">Step 3 / 3</p>
          <h1 className="text-2xl font-bold">Install the mobile app</h1>
          <p className="text-sm text-muted-foreground">
            Monitor your bots on the go. Pair your phone to this node in
            seconds.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex justify-center pb-2">
                <Smartphone className="size-12 text-primary" />
              </div>
              <CardTitle>1. Download the app</CardTitle>
              <CardDescription>
                Available on iOS and Android.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-3">
              <a
                href={APP_STORE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
              >
                <svg viewBox="0 0 24 24" className="size-5" fill="currentColor">
                  <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
                </svg>
                App Store
              </a>
              <a
                href={PLAY_STORE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
              >
                <svg viewBox="0 0 24 24" className="size-5" fill="currentColor">
                  <path d="M3.609 1.814L13.792 12 3.61 22.186a.996.996 0 0 1-.61-.92V2.734a1 1 0 0 1 .609-.92zm10.89 10.893l2.302 2.302-10.937 6.333 8.635-8.635zm3.199-3.199l2.807 1.626a1 1 0 0 1 0 1.732l-2.807 1.626L15.206 12l2.492-2.492zM5.864 2.658L16.8 8.99l-2.302 2.302-8.634-8.634z" />
                </svg>
                Google Play
              </a>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex justify-center pb-2">
                <svg
                  viewBox="0 0 24 24"
                  className="size-12 text-primary"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.5}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="3" y="3" width="7" height="7" rx="1" />
                  <rect x="14" y="3" width="7" height="7" rx="1" />
                  <rect x="3" y="14" width="7" height="7" rx="1" />
                  <rect x="14" y="14" width="3" height="3" />
                  <path d="M21 14h-3v3" />
                  <path d="M14 21v-3h3" />
                  <path d="M21 21h-3v-3" />
                </svg>
              </div>
              <CardTitle>2. Pair to this node</CardTitle>
              <CardDescription>
                Scan the QR code below from the mobile app to connect.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-4">
              {!showQr ? (
                <Button variant="outline" onClick={revealQr}>
                  Show QR code
                </Button>
              ) : (
                <>
                  <div className="flex items-start gap-2 rounded-md border border-yellow-500/40 bg-yellow-500/10 p-3 text-sm text-yellow-600 dark:text-yellow-400 w-full">
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
              <p className="text-xs text-center text-muted-foreground">
                You can also pair later from{" "}
                <Link
                  to="/settings"
                  className="underline underline-offset-4 hover:text-foreground"
                  onClick={() => sessionStorage.removeItem("setup_in_progress")}
                >
                  Settings
                </Link>
                .
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-center">
          <button
            onClick={finishSetup}
            className="text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  )
}
