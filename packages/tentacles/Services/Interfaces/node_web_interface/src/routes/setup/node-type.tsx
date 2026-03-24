import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router"
import { useMutation } from "@tanstack/react-query"
import { Network, Server } from "lucide-react"

import { SetupService, type ApiError, type SetupResult } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export const Route = createFileRoute("/setup/node-type")({
  beforeLoad: () => {
    if (!sessionStorage.getItem("setup_passphrase")) {
      throw redirect({ to: "/setup" })
    }
  },
  component: SetupNodeType,
  head: () => ({
    meta: [{ title: "Setup — Step 2" }],
  }),
})

function SetupNodeType() {
  const navigate = useNavigate()
  const { showErrorToast } = useCustomToast()

  const initMutation = useMutation<SetupResult, ApiError, "standalone" | "master">({
    mutationFn: (nodeType: "standalone" | "master") => {
      const passphrase = sessionStorage.getItem("setup_passphrase") ?? ""
      const privateKey = sessionStorage.getItem("setup_private_key") ?? undefined
      return SetupService.initSetup({
        requestBody: { passphrase, node_type: nodeType, private_key: privateKey || undefined },
      })
    },
    onSuccess: (result) => {
      const passphrase = sessionStorage.getItem("setup_passphrase") ?? ""
      localStorage.setItem("auth_username", result.address)
      localStorage.setItem("auth_password", passphrase)
      sessionStorage.removeItem("setup_passphrase")
      sessionStorage.removeItem("setup_private_key")
      navigate({ to: "/setup/first-bot" })
    },
    onError: (error) => {
      handleError.bind(showErrorToast)(error as ApiError)
    },
  })

  const select = () => {
    if (initMutation.isPending) return
    initMutation.mutate("standalone")
  }

  return (
    <div className="flex min-h-svh items-center justify-center p-6">
      <div className="flex w-full max-w-2xl flex-col gap-8">
        <div className="flex flex-col items-center gap-2 text-center">
          <p className="text-xs text-muted-foreground">Step 2 / 3</p>
          <h1 className="text-2xl font-bold">Node type</h1>
          <p className="text-sm text-muted-foreground">
            Your node will be initialized as a standalone node.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Card className="border-primary bg-primary/5">
            <CardHeader>
              <div className="flex justify-center pb-2">
                <Server className="size-12 text-primary" />
              </div>
              <CardTitle>Standalone Node</CardTitle>
              <CardDescription>
                Run everything on one machine. Perfect for getting started.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex justify-end">
              <Button disabled={initMutation.isPending} onClick={select}>
                Continue
              </Button>
            </CardContent>
          </Card>

          <Card className="relative opacity-50 cursor-not-allowed">
            <span className="absolute -top-2 right-3 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground border">
              Coming soon
            </span>
            <CardHeader>
              <div className="flex justify-center pb-2">
                <Network className="size-12 text-muted-foreground" />
              </div>
              <CardTitle>Master / Replica Node</CardTitle>
              <CardDescription>
                Orchestrate multiple worker nodes. For advanced distributed setups.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex justify-end">
              <Button variant="outline" disabled>
                Not available yet
              </Button>
            </CardContent>
          </Card>
        </div>

        <p className="text-center text-xs text-muted-foreground">
          The node type can be changed later using the <code>--node-type</code> CLI flag.
        </p>
      </div>
    </div>
  )
}
