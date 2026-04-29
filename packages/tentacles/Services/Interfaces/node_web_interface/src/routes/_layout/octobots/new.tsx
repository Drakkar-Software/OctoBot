import { createFileRoute } from "@tanstack/react-router"

import { NewBotCards } from "@/components/Common/NewBotCards"

export const Route = createFileRoute("/_layout/octobots/new")({
  component: NewOctobot,
  head: () => ({
    meta: [{ title: "New OctoBot" }],
  }),
})

function NewOctobot() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Create a new OctoBot</h1>
        <p className="text-md text-muted-foreground">
          Choose how to start your OctoBot. You can select a pre-configured setup, design your own strategy, or start with a custom configuration for full control. Each option is tailored to different levels of experience and customization needs.
        </p>
      </div>
      <NewBotCards />
    </div>
  )
}
