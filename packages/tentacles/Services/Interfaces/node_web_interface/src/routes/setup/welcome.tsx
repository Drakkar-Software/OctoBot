import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"

import { SetupService } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { useFirstRunMobileUi } from "@/hooks/useFirstRunMobileUi"
import {
  buildMobileUiUrl,
  MOBILE_UI_STATUS_POLL_MS,
} from "@/lib/mobile-ui"
import {
  evaluateFirstRunWelcomeTick,
  FIRST_RUN_CONFIGURED_LOGIN_HINT,
  FIRST_RUN_WELCOME_DESCRIPTION,
  FIRST_RUN_WELCOME_DOWNLOAD_LABEL,
  FIRST_RUN_WELCOME_DOWNLOADING_LABEL,
  FIRST_RUN_WELCOME_OPEN_LABEL,
  FIRST_RUN_WELCOME_RECOMMENDED_LABEL,
  FIRST_RUN_WELCOME_TITLE,
  getFirstRunFailureMessage,
  resolveFirstRunWelcomeMobileAction,
  shouldResumeFirstRunDownload,
  type FirstRunWelcomePhase,
} from "@/lib/first-run-mobile-ui"
import { markNodeAlreadyInitialized } from "@/lib/setup-conflict"

export const Route = createFileRoute("/setup/welcome")({
  component: SetupWelcome,
  head: () => ({
    meta: [{ title: "Setup - Welcome" }],
  }),
})

function SetupWelcome() {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<FirstRunWelcomePhase>("choose")
  const [failureMessage, setFailureMessage] = useState<string | null>(null)
  const openedMobileRef = useRef(false)
  const statusEnabled =
    phase === "choose" || phase === "downloading" || phase === "failed"
  const downloadInProgress = phase === "downloading"

  const {
    status,
    firstRunConflict,
    install,
    isInstallPending,
    statusError,
    installError,
  } = useFirstRunMobileUi({ statusEnabled, downloadInProgress })

  const setupStatusQuery = useQuery({
    queryKey: ["setup-status", "welcome"],
    queryFn: () => SetupService.getSetupStatus(),
    enabled: statusEnabled,
    refetchInterval: downloadInProgress ? MOBILE_UI_STATUS_POLL_MS : false,
    refetchOnWindowFocus: false,
  })

  const nodeConfigured = setupStatusQuery.data?.configured === true

  useEffect(() => {
    if (shouldResumeFirstRunDownload(phase, status)) {
      setPhase("downloading")
      openedMobileRef.current = false
    }
  }, [phase, status])

  useEffect(() => {
    if (!downloadInProgress) {
      return
    }
    const tick = evaluateFirstRunWelcomeTick(
      status,
      setupStatusQuery.data?.configured,
      firstRunConflict,
      phase,
    )
    if (tick.action === "login") {
      setPhase("configured_login")
      return
    }
    if (tick.action === "failed") {
      setFailureMessage(tick.failureMessage ?? null)
      setPhase("failed")
      return
    }
    if (tick.action === "open_mobile" && !openedMobileRef.current) {
      openedMobileRef.current = true
      void (async () => {
        const freshSetup = await SetupService.getSetupStatus()
        if (freshSetup.configured) {
          setPhase("configured_login")
          openedMobileRef.current = false
          return
        }
        if (status?.state !== "ready") {
          openedMobileRef.current = false
          return
        }
        window.location.assign(buildMobileUiUrl(undefined, window.location.origin))
      })()
    }
  }, [
    downloadInProgress,
    firstRunConflict,
    setupStatusQuery.data?.configured,
    status,
    phase,
  ])

  useEffect(() => {
    if (statusError || installError) {
      const err = statusError ?? installError
      const statusCode =
        typeof err === "object" && err && "status" in err
          ? (err as { status?: number }).status
          : undefined
      if (statusCode === 409) {
        setPhase("configured_login")
      }
    }
  }, [statusError, installError])

  const startMobile2Download = () => {
    setFailureMessage(null)
    setPhase("downloading")
    openedMobileRef.current = false
    install()
  }

  const openMobile2 = () => {
    window.location.assign(buildMobileUiUrl(undefined, window.location.origin))
  }

  const goToLogin = () => {
    markNodeAlreadyInitialized()
    navigate({ to: "/login" })
  }

  const showMobile2Panel =
    phase === "choose" || phase === "downloading" || phase === "failed"

  const mobileAction = resolveFirstRunWelcomeMobileAction(
    phase,
    status,
    nodeConfigured,
  )

  return (
    <AuthLayout wide>
      <div className="mx-auto flex w-full flex-col gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-bold">Welcome to OctoBot Node</h1>
          <p className="text-sm text-muted-foreground">
            Choose how you want to set up your Node.
          </p>
        </div>

        <div className="rounded-lg border border-border p-4 flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <div className="flex w-full flex-nowrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold whitespace-nowrap">
                {FIRST_RUN_WELCOME_TITLE}
              </h2>
              <Badge variant="frost" className="shrink-0">
                {FIRST_RUN_WELCOME_RECOMMENDED_LABEL}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {FIRST_RUN_WELCOME_DESCRIPTION}
            </p>
          </div>

          {phase === "configured_login" ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-muted-foreground">
                {FIRST_RUN_CONFIGURED_LOGIN_HINT}
              </p>
              <Button type="button" onClick={goToLogin}>
                Sign in
              </Button>
            </div>
          ) : null}

          {showMobile2Panel && phase === "failed" ? (
            <div className="flex flex-col gap-3">
              {failureMessage ?? getFirstRunFailureMessage(status) ? (
                <p className="text-destructive text-sm">
                  {failureMessage ?? getFirstRunFailureMessage(status)}
                </p>
              ) : null}
              <LoadingButton
                type="button"
                loading={isInstallPending}
                onClick={startMobile2Download}
              >
                Retry download
              </LoadingButton>
            </div>
          ) : null}

          {showMobile2Panel && phase !== "failed" ? (
            <div className="flex flex-col gap-3">
              {mobileAction === "busy" ? (
                <>
                  <Button type="button" disabled>
                    {FIRST_RUN_WELCOME_DOWNLOADING_LABEL}
                  </Button>
                  <p className="text-sm text-muted-foreground">
                    Verifying the bundle. This can take a minute.
                  </p>
                </>
              ) : null}
              {mobileAction === "open" ? (
                <Button type="button" onClick={openMobile2}>
                  {FIRST_RUN_WELCOME_OPEN_LABEL}
                </Button>
              ) : null}
              {mobileAction === "download" ? (
                <LoadingButton
                  type="button"
                  loading={isInstallPending}
                  onClick={startMobile2Download}
                >
                  {FIRST_RUN_WELCOME_DOWNLOAD_LABEL}
                </LoadingButton>
              ) : null}
            </div>
          ) : null}
        </div>

        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={() => navigate({ to: "/setup" })}
        >
          Set up with the Node wizard
        </Button>
      </div>
    </AuthLayout>
  )
}