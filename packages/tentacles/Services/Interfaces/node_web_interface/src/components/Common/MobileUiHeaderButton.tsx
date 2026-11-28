import { Download, ExternalLink, Loader2 } from "lucide-react"
import { useState } from "react"

import { OpenAPI } from "@/client"
import { MobileUiDialog } from "@/components/Setup/MobileUiDialog"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { useMobileUi } from "@/hooks/useMobileUi"
import {
  buildMobileUiUrl,
  getMobileUiHeaderAction,
  getMobileUiView,
  MOBILE_UI_HEADER_LABEL_GET,
  MOBILE_UI_HEADER_LABEL_INSTALLED,
  MOBILE_UI_HEADER_LABEL_INSTALLING,
} from "@/lib/mobile-ui"

export function MobileUiHeaderButton() {
  const { user } = useAuth()
  const { status, isLoading } = useMobileUi()
  const [dialogOpen, setDialogOpen] = useState(false)

  const isAdmin = user?.is_superuser === true
  const view = getMobileUiView(status, isAdmin)
  const action = getMobileUiHeaderAction(view)

  if (isLoading) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled
        aria-busy="true"
        aria-hidden
      >
        <ExternalLink className="size-4" />
        <span className="hidden sm:inline">
          {MOBILE_UI_HEADER_LABEL_INSTALLED}
        </span>
      </Button>
    )
  }

  if (action.kind === "hidden") {
    return null
  }

  const openUrl = buildMobileUiUrl(OpenAPI.BASE, window.location.origin)

  const openDialog = () => setDialogOpen(true)

  return (
    <>
      {action.kind === "open" ? (
        <Button asChild variant="outline" size="sm">
          <a
            href={openUrl}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={MOBILE_UI_HEADER_LABEL_INSTALLED}
          >
            <ExternalLink className="size-4" />
            <span className="hidden sm:inline">
              {MOBILE_UI_HEADER_LABEL_INSTALLED}
            </span>
          </a>
        </Button>
      ) : action.kind === "installing" ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-label={MOBILE_UI_HEADER_LABEL_INSTALLING}
          onClick={openDialog}
        >
          <Loader2 className="size-4 animate-spin" />
          <span className="hidden sm:inline">
            {MOBILE_UI_HEADER_LABEL_INSTALLING}
          </span>
        </Button>
      ) : (
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-label={MOBILE_UI_HEADER_LABEL_GET}
          onClick={openDialog}
        >
          <Download className="size-4" />
          <span className="hidden sm:inline">{MOBILE_UI_HEADER_LABEL_GET}</span>
        </Button>
      )}
      {dialogOpen ? (
        <MobileUiDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          readyLabel="Open"
        />
      ) : null}
    </>
  )
}