import {
  createFileRoute,
  redirect,
  useNavigate,
} from "@tanstack/react-router"

import { ConnectNodeGuide } from "@/components/Setup/ConnectNodeGuide"
import { SetupStepHeader } from "@/components/Setup/SetupStepHeader"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import {
  CONNECT_NODE_PAGE_SUBTITLE,
  CONNECT_NODE_PAGE_TITLE,
} from "@/lib/ui-connect"

export const Route = createFileRoute("/setup/connect")({
  beforeLoad: () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/setup" })
    }
  },
  component: SetupConnect,
  head: () => ({
    meta: [{ title: "Setup - Connect" }],
  }),
})

function SetupConnect() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-svh items-center justify-center p-6">
      <div className="flex w-full max-w-3xl flex-col gap-8">
        <SetupStepHeader
          step={2}
          total={3}
          title={CONNECT_NODE_PAGE_TITLE}
          subtitle={CONNECT_NODE_PAGE_SUBTITLE}
        />

        <ConnectNodeGuide />

        <div className="flex flex-col items-center gap-3">
          <Button
            type="button"
            onClick={() => navigate({ to: "/setup/first-bot" })}
          >
            Continue
          </Button>
        </div>
      </div>
    </div>
  )
}
