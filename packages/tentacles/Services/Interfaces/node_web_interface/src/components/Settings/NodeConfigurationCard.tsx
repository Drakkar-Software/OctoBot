import { useMutation } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Check, Power, Sliders } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { NodesService } from "@/client"
import { CardCornerButton } from "@/components/Settings/CardCornerButton"
import { CloudSyncSection } from "@/components/Settings/CloudSyncCard"
import { NodeBrowserAppCompactSection } from "@/components/Settings/NodeBrowserAppCompactSection"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { useMobileUi } from "@/hooks/useMobileUi"
import { getMobileUiView } from "@/lib/mobile-ui"
import { buildAuthHeader, fetchNodeConfig } from "@/lib/node-config"

type NodeType = "standalone" | "master"

const WEBSITE_SECTION_LABEL = "Website & mobile apps"
const WEBSITE_SECTION_DESCRIPTION =
  "Use the website or iOS/Android apps (not this node's browser app)."

const HOST_INPUT_CLASS =
  "w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
const HOST_SAVE_BUTTON_CLASS =
  "inline-flex shrink-0 items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-accent"
const HOST_PLACEHOLDER = "my-node.tailnet.ts.net"

const SETTINGS_CARD_NAV_LINK_CLASS =
  "text-sm underline underline-offset-4 hover:text-foreground w-fit"

function WebsiteAndMobileAppsSection() {
  return (
    <div className="flex flex-col gap-3">
      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {WEBSITE_SECTION_LABEL}
      </span>
      <p className="text-sm text-muted-foreground">{WEBSITE_SECTION_DESCRIPTION}</p>
      <Link to="/settings/connect" className={SETTINGS_CARD_NAV_LINK_CLASS}>
        Open connect guide
      </Link>
    </div>
  )
}

export function NodeConfigurationCard() {
  const { user } = useAuth()
  const { status, isLoading: isMobileUiLoading } = useMobileUi()
  const isAdmin = user?.is_superuser === true
  const browserAppView = getMobileUiView(status, isAdmin)
  const showBrowserAppSection =
    isMobileUiLoading || browserAppView.kind !== "hidden"
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [stopDialogOpen, setStopDialogOpen] = useState(false)
  // Node type is currently a hidden section (see CardContent below) — kept
  // only so re-enabling it doesn't need the fetch re-wired.
  const [, setNodeType] = useState<NodeType | null>(null)
  const [externalHost, setExternalHost] = useState("")
  const [envOverride, setEnvOverride] = useState(false)
  const [hostStatus, setHostStatus] = useState<
    "loading" | "ready" | "saving" | "saved" | "error"
  >("loading")
  const [hostError, setHostError] = useState("")
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const stopMutation = useMutation({
    mutationFn: () => NodesService.stopNode(),
    onSuccess: () => {
      setStopDialogOpen(false)
      showSuccessToast("OctoBot is stopping")
    },
    onError: (error) =>
      showErrorToast(
        error instanceof Error ? error.message : "Couldn't stop the node",
      ),
  })

  useEffect(() => {
    void (async () => {
      try {
        const data = await fetchNodeConfig()
        setNodeType(data.node_type ?? "standalone")
        setExternalHost(data.external_host ?? "")
        setEnvOverride(Boolean(data.external_host_env_override))
        setHostStatus("ready")
      } catch (error) {
        console.error(
          "NodeConfigurationCard: failed to load host configuration",
          error,
        )
        setNodeType("standalone")
        setHostStatus("error")
        setHostError("Failed to load host configuration.")
      }
    })()
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const handleSaveHost = async () => {
    setHostStatus("saving")
    setHostError("")
    try {
      const res = await fetch("/api/v1/nodes/config", {
        method: "PATCH",
        headers: {
          Authorization: await buildAuthHeader(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ external_host: externalHost }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setExternalHost(data.external_host ?? "")
      setHostStatus("saved")
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setHostStatus("ready"), 2000)
    } catch (e) {
      console.error("NodeConfigurationCard: failed to save host configuration", e)
      setHostStatus("error")
      setHostError(e instanceof Error ? e.message : "Failed to save host")
    }
  }

  return (
    <>
      <Card className="relative">
        {user?.is_superuser && (
          <CardCornerButton
            icon={Power}
            label="Stop node"
            variant="destructive"
            onClick={() => setStopDialogOpen(true)}
          />
        )}
        <CardHeader className={user?.is_superuser ? "pr-12" : undefined}>
          <CardTitle className="flex items-center gap-2">
            <Sliders className="size-4" />
            Node configuration
          </CardTitle>
          <CardDescription>
            How this node runs and the address clients use to reach it.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {/* Node type — hidden, not removed. Only "standalone" is
              selectable today (master/replica is "Coming soon"), so this
              section currently offers nothing to act on. Re-add the
              `Network, Server` lucide-react imports if this is restored.
          <div className="flex flex-col gap-3">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Node type
            </span>
            <div className="grid grid-cols-2 gap-3">
              <div
                className={`flex items-center justify-center gap-2 rounded-lg border p-2 text-sm ${
                  nodeType === "standalone"
                    ? "border-primary bg-primary/5 text-primary"
                    : "text-muted-foreground"
                }`}
              >
                <Server className="size-4" />
                Standalone
              </div>
              <div className="relative flex items-center justify-center gap-2 rounded-lg border p-2 text-sm opacity-50 cursor-not-allowed text-muted-foreground">
                <Network className="size-4" />
                Master / Replica
                <span className="absolute -top-2 right-2 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground border">
                  Coming soon
                </span>
              </div>
            </div>
            <span className="text-xs text-muted-foreground">
              The node type can only be changed from the CLI. Use the{" "}
              <code>--node-type</code> flag when starting the node.
            </span>
          </div>
          <div className="border-t" />
          */}
          {showBrowserAppSection ? (
            <>
              <NodeBrowserAppCompactSection />
              <div className="border-t" />
            </>
          ) : null}
          <WebsiteAndMobileAppsSection />
          <div className="border-t" />
          <div
            className="flex flex-col gap-3"
            aria-busy={hostStatus === "loading" || undefined}
          >
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Host
            </span>
            {hostStatus === "loading" ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  className={HOST_INPUT_CLASS}
                  placeholder={HOST_PLACEHOLDER}
                  disabled
                  readOnly
                  value=""
                  aria-hidden
                />
                <button
                  type="button"
                  className={HOST_SAVE_BUTTON_CLASS}
                  disabled
                  aria-hidden
                >
                  Save
                </button>
              </div>
            ) : envOverride ? (
              <>
                <div className="min-h-[38px] w-full rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground flex items-center">
                  {externalHost || "(empty)"}
                </div>
                <span className="text-xs text-muted-foreground">
                  Set via the <code>NODE_EXTERNAL_HOST</code> environment
                  variable; remove it to edit this value here.
                </span>
              </>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    className={HOST_INPUT_CLASS}
                    placeholder={HOST_PLACEHOLDER}
                    value={externalHost}
                    onChange={(e) => setExternalHost(e.target.value)}
                  />
                  <button
                    type="button"
                    className={HOST_SAVE_BUTTON_CLASS}
                    onClick={handleSaveHost}
                    disabled={hostStatus === "saving"}
                  >
                    {hostStatus === "saved" ? (
                      <Check className="size-4" />
                    ) : null}
                    {hostStatus === "saved"
                      ? "Saved"
                      : hostStatus === "saving"
                        ? "Saving…"
                        : "Save"}
                  </button>
                </div>
                {hostStatus === "error" && (
                  <span className="text-xs text-destructive">{hostError}</span>
                )}
              </>
            )}
            <span className="text-xs text-muted-foreground">
              Address clients use to reach this node (e.g. Tailscale).
            </span>
          </div>
          <div className="border-t" />
          <CloudSyncSection />
        </CardContent>
      </Card>

      <Dialog open={stopDialogOpen} onOpenChange={setStopDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Stop node</DialogTitle>
            <DialogDescription>
              This will stop the OctoBot process on this machine. Running
              OctoBots will be interrupted and the web interface will become
              unavailable until OctoBot is started again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" type="button">
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              loading={stopMutation.isPending}
              onClick={() => stopMutation.mutate()}
            >
              Stop node
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}