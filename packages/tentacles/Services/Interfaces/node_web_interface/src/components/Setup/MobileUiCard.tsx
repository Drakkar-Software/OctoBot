import { OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"
import { useMobileUi } from "@/hooks/useMobileUi"
import {
  buildMobileUiUrl,
  getMobileUiView,
  isMobileUiUpToDate,
  MOBILE_UI_DESCRIPTION,
  MOBILE_UI_TITLE,
  type MobileUiView,
} from "@/lib/mobile-ui"

export type MobileUiPanelProps = {
  view: MobileUiView
  onInstall: () => void
  onCheck: () => void
  installPending: boolean
  checkPending: boolean
  upToDate: boolean
  openUrl: string
}

export function MobileUiPanel({
  view,
  onInstall,
  onCheck,
  installPending,
  checkPending,
  upToDate,
  openUrl,
}: MobileUiPanelProps) {
  if (view.kind === "hidden") {
    return null
  }

  const showDownloading =
    view.kind === "installing" ||
    (view.kind === "install" && installPending)

  return (
    <div className="flex flex-col gap-3">
      {view.kind === "install" && !installPending && (
        <>
          <Button type="button" onClick={onInstall}>
            Download
          </Button>
          {view.error ? (
            <p className="text-destructive text-sm">{view.error}</p>
          ) : null}
        </>
      )}
      {showDownloading ? (
        <>
          <Button type="button" disabled>
            Downloading...
          </Button>
          <p className="text-sm text-muted-foreground">
            This can take a minute.
          </p>
        </>
      ) : null}
      {view.kind === "ready" ? (
        <>
          <a href={openUrl} target="_blank" rel="noopener noreferrer">
            <Button type="button">Open</Button>
          </a>
          {view.version ? (
            <p className="text-xs text-muted-foreground">
              Version {view.version}
            </p>
          ) : null}
          {view.canCheckForUpdates ? (
            view.updateAvailable ? (
              <>
                <p className="text-sm text-muted-foreground">
                  {view.latestVersion
                    ? `New version available: ${view.latestVersion}`
                    : "New version available."}
                </p>
                <Button
                  type="button"
                  onClick={onInstall}
                  disabled={installPending}
                >
                  Update
                </Button>
              </>
            ) : (
              <>
                <Button
                  type="button"
                  variant="outline"
                  onClick={onCheck}
                  disabled={checkPending}
                >
                  {checkPending ? "Checking..." : "Check for updates"}
                </Button>
                {upToDate ? (
                  <p className="text-sm text-muted-foreground">
                    You have the latest version.
                  </p>
                ) : null}
              </>
            )
          ) : null}
          {view.error ? (
            <p className="text-destructive text-sm">{view.error}</p>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

export function MobileUiCardView({
  view,
  onInstall,
  onCheck,
  installPending,
  checkPending,
  upToDate,
  openUrl,
}: MobileUiPanelProps) {
  if (view.kind === "hidden") {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{MOBILE_UI_TITLE}</CardTitle>
        <CardDescription>{MOBILE_UI_DESCRIPTION}</CardDescription>
      </CardHeader>
      <CardContent>
        <MobileUiPanel
          view={view}
          onInstall={onInstall}
          onCheck={onCheck}
          installPending={installPending}
          checkPending={checkPending}
          upToDate={upToDate}
          openUrl={openUrl}
        />
      </CardContent>
    </Card>
  )
}

export function MobileUiCard() {
  const { user } = useAuth()
  const {
    status,
    install,
    check,
    isInstallRequestPending,
    isCheckRequestPending,
    checkSucceeded,
  } = useMobileUi()
  const isAdmin = user?.is_superuser === true
  const view = getMobileUiView(status, isAdmin)

  if (view.kind === "hidden") {
    return null
  }

  const openUrl = buildMobileUiUrl(OpenAPI.BASE, window.location.origin)
  const upToDate = isMobileUiUpToDate(view, checkSucceeded)

  return (
    <MobileUiCardView
      view={view}
      onInstall={install}
      onCheck={check}
      installPending={isInstallRequestPending}
      checkPending={isCheckRequestPending}
      upToDate={upToDate}
      openUrl={openUrl}
    />
  )
}
