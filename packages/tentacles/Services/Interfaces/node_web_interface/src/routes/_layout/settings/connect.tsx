import { createFileRoute, useNavigate } from "@tanstack/react-router"

import { ConnectNodeGuide } from "@/components/Setup/ConnectNodeGuide"
import {
  CONNECT_NODE_PAGE_SUBTITLE,
  CONNECT_NODE_PAGE_TITLE,
} from "@/lib/ui-connect"

export const Route = createFileRoute("/_layout/settings/connect")({
  component: SettingsConnect,
  head: () => ({
    meta: [{ title: "Connect to OctoBot interface" }],
  }),
})

function SettingsConnect() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col gap-8">
      <div className="mx-auto w-full max-w-3xl text-center">
        <h1 className="text-2xl font-bold tracking-tight">
          {CONNECT_NODE_PAGE_TITLE}
        </h1>
        <p className="text-md text-muted-foreground">
          {CONNECT_NODE_PAGE_SUBTITLE}
        </p>
      </div>

      <div className="mx-auto flex w-full max-w-3xl flex-col gap-8">
        <ConnectNodeGuide />

        <div className="flex justify-center">
          <button
            type="button"
            onClick={() => navigate({ to: "/settings" })}
            className="text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
          >
            Back to settings
          </button>
        </div>
      </div>
    </div>
  )
}
