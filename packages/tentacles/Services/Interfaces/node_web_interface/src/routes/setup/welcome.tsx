import { createFileRoute, useNavigate } from "@tanstack/react-router"

import { AuthLayout } from "@/components/Common/AuthLayout"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/setup/welcome")({
  component: SetupWelcome,
  head: () => ({
    meta: [{ title: "Setup - Welcome" }],
  }),
})

function SetupWelcome() {
  const navigate = useNavigate()

  return (
    <AuthLayout>
      <div className="mx-auto flex w-full max-w-md flex-col gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-bold">Welcome to OctoBot Node</h1>
          <div className="flex flex-col gap-3 text-sm text-muted-foreground">
            <p>
              OctoBot Node is your personal trading engine. It runs your OctoBots
              locally and keeps your keys on your machine.
            </p>
            <p>
              It connects to the OctoBot web or mobile interface for you to monitor
              and manage your bots from anywhere.
            </p>
            <p className="self-start w-full text-left">
              First, let&apos;s configure your node.
            </p>
          </div>
        </div>

        <ol className="flex list-decimal flex-col gap-3 pl-5 text-sm text-muted-foreground">
          <li>
            <span className="font-medium text-foreground">Set up your wallet</span>
            {" - "}
            create a new wallet or import an existing one. Your wallet is your
            node's cryptographic identity.
          </li>
          <li>
            <span className="font-medium text-foreground">Connect your interface</span>
            {" - "}
            link the OctoBot web or mobile app to this node.
          </li>
          <li>
            <span className="font-medium text-foreground">Launch your first OctoBot</span>
            {" - "}
            start a bot from the interface, or configure one manually on the node.
          </li>
        </ol>

        <Button
          type="button"
          className="w-full"
          onClick={() => navigate({ to: "/setup" })}
        >
          Get started
        </Button>
      </div>
    </AuthLayout>
  )
}
