import { OpenAPI } from "@/client"
import { BrowserAppOpenOrInstallCta } from "@/components/Common/BrowserAppOpenOrInstallCta"
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
  MOBILE_UI_DESCRIPTION,
  MOBILE_UI_TITLE,
} from "@/lib/mobile-ui"

export type MobileUiPanelProps = {
  readyLabel?: string
}

export function MobileUiPanel({
  readyLabel = "Open",
}: MobileUiPanelProps) {
  const openUrl = buildMobileUiUrl(OpenAPI.BASE, window.location.origin)
  return (
    <BrowserAppOpenOrInstallCta openHref={openUrl} readyLabel={readyLabel} />
  )
}

export function MobileUiCardView() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{MOBILE_UI_TITLE}</CardTitle>
        <CardDescription>{MOBILE_UI_DESCRIPTION}</CardDescription>
      </CardHeader>
      <CardContent>
        <MobileUiPanel />
      </CardContent>
    </Card>
  )
}

export function MobileUiCard() {
  const { user } = useAuth()
  const { status, isLoading } = useMobileUi()
  const isAdmin = user?.is_superuser === true
  const view = getMobileUiView(status, isAdmin)

  if (isLoading || view.kind !== "hidden") {
    return <MobileUiCardView />
  }

  return null
}