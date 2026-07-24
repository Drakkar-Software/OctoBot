import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router"

import { NewBotCards } from "@/components/Common/NewBotCards"
import { SetupStepHeader } from "@/components/Setup/SetupStepHeader"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/setup/first-bot")({
  beforeLoad: () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/setup" })
    }
  },
  component: SetupFirstBot,
  head: () => ({
    meta: [{ title: "Setup - First OctoBot" }],
  }),
})

function SetupFirstBot() {
  const navigate = useNavigate()

  const finishSetup = () => {
    sessionStorage.removeItem("setup_in_progress")
    navigate({ to: "/" })
  }

  return (
    <div className="flex min-h-svh items-center justify-center p-6">
      <div className="flex w-full max-w-4xl flex-col gap-8">
        <SetupStepHeader
          step={3}
          total={3}
          title="Launch your first OctoBot"
          subtitle="Pick how to create your first bot, or skip and do it later."
        />

        <NewBotCards onFinishSetup={finishSetup} />

        <div className="flex justify-center">
          <button
            type="button"
            onClick={finishSetup}
            className="text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  )
}
