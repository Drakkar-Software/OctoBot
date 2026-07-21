import { useMutation } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Bug, Check, Code, Network, Power, Server, Sliders } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { NodesService } from "@/client"
import { CardCornerButton } from "@/components/Settings/CardCornerButton"
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
import { buildAuthHeader, fetchNodeConfig } from "@/lib/node-config"

type NodeType = "standalone" | "master"

export function NodeConfigurationCard() {
  const { user } = useAuth()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [stopDialogOpen, setStopDialogOpen] = useState(false)
  const [nodeType, setNodeType] = useState<NodeType | null>(null)
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
      } catch {
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
          <div className="flex flex-col gap-3">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Host
            </span>
            {hostStatus === "loading" ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
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
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                    placeholder="my-node.tailnet.ts.net"
                    value={externalHost}
                    onChange={(e) => setExternalHost(e.target.value)}
                  />
                  <button
                    type="button"
                    className="inline-flex shrink-0 items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-accent"
                    onClick={handleSaveHost}
                    disabled={hostStatus === "saving"}
                  >
                    {hostStatus === "saved" ? <Check className="size-4" /> : null}
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
              Host (and port, if non-default) clients use to reach this node —
              required behind a reverse proxy that rewrites the Host header
              (e.g. <code>tailscale serve</code>).
            </span>
          </div>
          <div className="border-t" />
          <div className="flex flex-col gap-3">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Expert
            </span>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link to="/debug">
                  <Bug className="size-4" />
                  Debug view
                </Link>
              </Button>
              <Button variant="outline" size="sm" asChild>
                <Link to="/dsl-keywords">
                  <Code className="size-4" />
                  DSL keywords
                </Link>
              </Button>
            </div>
          </div>

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
