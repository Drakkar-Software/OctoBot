import { createFileRoute, Link, redirect } from "@tanstack/react-router"

import { NewBotCards } from "@/components/Common/NewBotCards"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/setup/first-bot")({
  beforeLoad: () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/setup" })
    }
  },
  component: SetupFirstBot,
  head: () => ({
    meta: [{ title: "Setup — First OctoBot" }],
  }),
})

function SetupFirstBot() {
  return (
    <div className="flex min-h-svh items-center justify-center p-6">
      <div className="flex w-full max-w-4xl flex-col gap-8">
        <div className="flex flex-col items-center gap-2 text-center">
          <p className="text-xs text-muted-foreground">Step 2 / 3</p>
          <h1 className="text-2xl font-bold">Launch your first OctoBot</h1>
          <p className="text-sm text-muted-foreground">
            Pick how to create your first bot, or skip and do it later.
          </p>
        </div>

        <NewBotCards />

        <div className="flex justify-center">
          <Link
            to="/setup/mobile-app"
            className="text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
          >
            Skip for now
          </Link>
        </div>
      </div>
    </div>
  )
}
