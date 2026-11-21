import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { useMobileUi } from "@/hooks/useMobileUi"
import { getMobileUiView } from "@/lib/mobile-ui"

const DEFAULT_READY_LABEL = "Open browser app"

export type BrowserAppOpenOrInstallCtaProps = {
  openHref: string
  readyLabel?: string
}

export function BrowserAppOpenOrInstallCta({
  openHref,
  readyLabel = DEFAULT_READY_LABEL,
}: BrowserAppOpenOrInstallCtaProps) {
  const { user } = useAuth()
  const { install, isInstallRequestPending, isLoading, status } = useMobileUi()
  const isAdmin = user?.is_superuser === true
  const view = getMobileUiView(status, isAdmin)

  if (isLoading) {
    return (
      <Button type="button" size="sm" disabled aria-busy="true">
        {readyLabel}
      </Button>
    )
  }

  if (view.kind === "hidden") {
    return null
  }

  const showDownloading =
    view.kind === "installing" ||
    (view.kind === "install" && isInstallRequestPending)

  if (showDownloading) {
    return (
      <div className="flex flex-col items-start gap-2">
        <Button type="button" size="sm" disabled>
          Downloading...
        </Button>
        <p className="text-xs text-muted-foreground">
          This can take a minute.
        </p>
      </div>
    )
  }

  if (view.kind === "install") {
    return (
      <div className="flex flex-col items-start gap-2">
        <Button type="button" size="sm" onClick={install}>
          Download
        </Button>
        {view.error ? (
          <p className="text-sm text-destructive">{view.error}</p>
        ) : null}
      </div>
    )
  }

  if (view.kind === "ready") {
    return (
      <Button type="button" size="sm" asChild>
        <a href={openHref} target="_blank" rel="noopener noreferrer">
          {readyLabel}
        </a>
      </Button>
    )
  }

  return null
}