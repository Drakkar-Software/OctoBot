import { useMutation } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Bug, Power, Server } from "lucide-react"
import { useState } from "react"

import { NodesService } from "@/client"
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

export function NodeManagementCard() {
  const { user } = useAuth()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [stopDialogOpen, setStopDialogOpen] = useState(false)

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

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="size-4" />
            Node management
          </CardTitle>
          <CardDescription>
            Inspect runtime state, download logs, and run debug actions from the
            debug view.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-row flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to="/debug">
              <Bug className="size-4" />
              Debug view
            </Link>
          </Button>
          {user?.is_superuser && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setStopDialogOpen(true)}
            >
              <Power className="size-4" />
              Stop node
            </Button>
          )}
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
