import { Link } from "@tanstack/react-router"

import { OpenAPI } from "@/client"
import { BrowserAppOpenOrInstallCta } from "@/components/Common/BrowserAppOpenOrInstallCta"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { useMobileUi } from "@/hooks/useMobileUi"
import {
  buildMobileUiBotsNewUrl,
  getMobileUiView,
  isMobileUiOfferable,
} from "@/lib/mobile-ui"
import {
  OCTOBOT_CONNECT_GUIDE_URL,
  OCTOBOT_WEB_INTERFACE_URL,
} from "@/lib/external-links"

type StartAutomationDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAcknowledge?: () => void
}

const BROWSER_APP_CARD_LABEL = "OctoBot browser app (recommended)"
const BROWSER_APP_CARD_HELPER =
  "Create a new automation in the interface served by this node."

export function StartAutomationDialog({
  open,
  onOpenChange,
  onAcknowledge,
}: StartAutomationDialogProps) {
  const { user } = useAuth()
  const { status, isLoading } = useMobileUi()
  const isAdmin = user?.is_superuser === true
  const view = getMobileUiView(status, isAdmin)
  const showBrowserAppCard = isMobileUiOfferable(isLoading, view)
  const botsNewUrl = buildMobileUiBotsNewUrl(
    OpenAPI.BASE,
    window.location.origin,
  )

  const handleAcknowledge = () => {
    onOpenChange(false)
    onAcknowledge?.()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Start your automation from the interface</DialogTitle>
          <DialogDescription asChild>
            <div className="flex flex-col gap-3 pt-1 text-sm text-muted-foreground">
              <p>
                Create and start your automation in the OctoBot browser app,
                website, or mobile app. It will appear on this node's dashboard
                once started.
              </p>
            </div>
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4 border-t pt-4">
          {showBrowserAppCard ? (
            <div
              className="flex flex-col gap-3 rounded-md border p-4"
              aria-busy={isLoading || undefined}
            >
              <span className="text-sm font-medium">
                {BROWSER_APP_CARD_LABEL}
              </span>
              <p className="text-sm text-muted-foreground">
                {BROWSER_APP_CARD_HELPER}
              </p>
              <BrowserAppOpenOrInstallCta
                openHref={botsNewUrl}
                readyLabel="Create in browser app"
              />
            </div>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2 rounded-md border p-4">
              <span className="text-sm font-medium">Website</span>
              <p className="text-sm text-muted-foreground">
                Open the{" "}
                <a
                  href={OCTOBOT_WEB_INTERFACE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-4 hover:text-foreground"
                >
                  hosted OctoBot web app
                </a>{" "}
                and create a new automation.
              </p>
            </div>
            <div className="flex flex-col gap-2 rounded-md border p-4">
              <span className="text-sm font-medium">Mobile app</span>
              <p className="text-sm text-muted-foreground">
                Open your OctoBot app and create a new automation.
              </p>
            </div>
          </div>
          <p className="text-center text-sm text-muted-foreground">
            Need help connecting your interface? See the{" "}
            <Link
              to="/settings/connect"
              className="underline underline-offset-4 hover:text-foreground"
            >
              quick step-by-step guide
            </Link>{" "}
            or the{" "}
            <a
              href={OCTOBOT_CONNECT_GUIDE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-4 hover:text-foreground"
            >
              detailed guide on octobot.cloud
            </a>{" "}
            if you have questions.
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
            >
              Close
            </Button>
            {onAcknowledge ? (
              <Button
                type="button"
                variant="outline"
                onClick={handleAcknowledge}
              >
                I will use the OctoBot interface
              </Button>
            ) : null}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}