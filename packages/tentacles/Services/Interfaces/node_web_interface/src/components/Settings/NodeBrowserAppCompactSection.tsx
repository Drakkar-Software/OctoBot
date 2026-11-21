import { useEffect, useRef } from "react"
import { OpenAPI } from "@/client"
import { BrowserAppOpenOrInstallCta } from "@/components/Common/BrowserAppOpenOrInstallCta"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { useMobileUi } from "@/hooks/useMobileUi"
import { buildMobileUiUrl, getMobileUiView, type MobileUiView } from "@/lib/mobile-ui"

const SECTION_LABEL = "OctoBot browser app"
const SECTION_DESCRIPTION =
  "The OctoBot interface served by this node in your browser."

const UPDATE_PILL_SLOT_CLASS = "min-w-[8.75rem] flex shrink-0 justify-end"

function ReservedUpdatePillSlot() {
  return (
    <span
      className="invisible inline-flex h-7 items-center rounded-full px-3 text-xs"
      aria-hidden
    >
      Update available
    </span>
  )
}

function SectionLabelRow({
  view,
  onUpdate,
  installPending,
}: {
  view: MobileUiView
  onUpdate: () => void
  installPending: boolean
}) {
  const showPill =
    view.kind === "ready" && view.updateAvailable

  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {SECTION_LABEL}
      </span>
      <div className={UPDATE_PILL_SLOT_CLASS}>
        {showPill ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 rounded-full px-3 text-xs"
            onClick={onUpdate}
            disabled={installPending}
          >
            {installPending ? "Updating…" : "Update available"}
          </Button>
        ) : (
          <ReservedUpdatePillSlot />
        )}
      </div>
    </div>
  )
}

function SectionLabelRowLoading() {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {SECTION_LABEL}
      </span>
      <div className={UPDATE_PILL_SLOT_CLASS}>
        <ReservedUpdatePillSlot />
      </div>
    </div>
  )
}

export function NodeBrowserAppCompactSection() {
  const { user } = useAuth()
  const {
    status,
    install,
    check,
    isInstallRequestPending,
    isLoading,
  } = useMobileUi()
  const isAdmin = user?.is_superuser === true
  const view = getMobileUiView(status, isAdmin)
  const didAutoCheck = useRef(false)

  useEffect(() => {
    if (isLoading) return
    if (didAutoCheck.current) return
    if (view.kind !== "ready" || !view.canCheckForUpdates) return
    didAutoCheck.current = true
    check()
  }, [isLoading, view, check])

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3" aria-busy="true">
        <SectionLabelRowLoading />
        <p className="text-sm text-muted-foreground">{SECTION_DESCRIPTION}</p>
        <BrowserAppOpenOrInstallCta
          openHref={buildMobileUiUrl(OpenAPI.BASE, window.location.origin)}
          readyLabel="Open"
        />
      </div>
    )
  }

  if (view.kind === "hidden") {
    return null
  }

  const openUrl = buildMobileUiUrl(OpenAPI.BASE, window.location.origin)

  return (
    <div className="flex flex-col gap-3">
      <SectionLabelRow
        view={view}
        onUpdate={install}
        installPending={isInstallRequestPending}
      />
      <p className="text-sm text-muted-foreground">{SECTION_DESCRIPTION}</p>
      <BrowserAppOpenOrInstallCta openHref={openUrl} readyLabel="Open" />
    </div>
  )
}